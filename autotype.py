import sys, json, time, keyboard
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, VerticalScroll
from textual.widgets import Static, Header, Footer, Tree, Button, Label, Input, TextArea
from textual.reactive import reactive

class Form(Static):
    """A widget to display a form."""
    
    data = reactive({
        "index": None,
    })
    
    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Label("Name:", classes="label", id="name-label"),
            Input(placeholder="Input name...", type="text", id="name"),
            Label("Command:", classes="label", id="command-label"),
            Input(placeholder="Input command...", type="text", id="command"),
            Label("Text:", classes="label", id="text-label"),
            TextArea(id="text"),
        )
    
    def on_input_changed(self, event: Input.Changed) -> None:
        input_value = event.input.value
        if event.input.id == "command":
            if not input_value.startswith("/"):
                event.input.value = f"/{input_value}"
                event.input.action_cursor_right()
                
        self.data = {**self.data, event.input.id: input_value}
        
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self.data = {**self.data, "text": event.text_area.text}
        row_count = len(event.text_area.text.split("\n"))
        event.text_area.move_cursor((row_count, 0))
        event.text_area.action_cursor_line_end()
        
    def watch_data(self, data: dict) -> None:
        self.query_one("#name").value = data.get("name", "")
        self.query_one("#command").value = data.get("command", "")
        self.query_one("#text").text = data.get("text", "")
    
class Content(Static):
    """A widget to display content."""
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the content."""
        yield TextOpening()
        yield Form(id="form")

class TextOpening(Static):
    """A widget to display content."""

    label = reactive("Commands")
        
    def watch_label(self, label: str) -> None:
        """Called when the label attribute changes."""
        self.update(f"Select Command: {label}")
        
class CommandList(Static):
    """A widget to display a list of commands."""

    commands = reactive([])
    
    # check if commands.json exists and load it, otherwise create it
    try:
        commands = reactive(json.load(open("commands.json")))
    except Exception:
        with open("commands.json", "w") as file:
            json.dump([], file, indent=2)

    def compose(self) -> ComposeResult:
        """Create child widgets for the command list."""
        
        tree: Tree[dict] = Tree("Commands")
        for index, command in enumerate(self.commands):
            if command['type'] == 'parent':
                branch = tree.root.add(command['name'], data={
                    "index": index,
                    "parent": None,
                    "type": "parent",
                    "name": command['name'],
                    "command": command['command'],
                    "text": command['text'],
                })
                for i, child in enumerate(command['children']):
                    branch.add_leaf(child["name"], data={
                        "index": i,
                        "parent": index,
                        "type": "child",
                        "name": child["name"],
                        "command": child["command"],
                        "text": child["text"],
                    })
            else:
                tree.root.add_leaf(command['name'], data={
                    "index": index,
                    "parent": None,
                    "type": "child",
                    "name": command['name'],
                    "command": command['command'],
                    "text": command['text'],
                })
            
            yield tree

    def watch_commands(self, commands: list) -> None:
        """Called when the commands attribute changes."""
        # self.commands = commands

class AutoTypeApp(App):
    """A Textual app to manage autotype."""

    CSS = """
        Screen {
            layers: below above;
        }

        Header {
            layer: above;
        }

        #buttons {
            height: 20%;
            padding: 0 2;
            grid-size: 3 1;
        }

        #buttons #start {
            dock: right;
        }

        #save, #add-child {
            display: none;
        }

        #content {
            padding-top: 1;
        }

        #content Content {
            height: 80%;
        }

        #content TextOpening {
            content-align: center middle;
            height: 100%;
        }

        #content #form {
            height: 100%;
            padding: 1;
        }

        #content #form .label{
            margin-top: 1;
            padding-left: 1;
        }

        .edit {
            content-align: left top;
        }

        #content Start {
            height: 20%;
            align: right middle;
            padding-right: 2;
        }

        #sidebar {
            display: block;
            dock: left;
            width: 20%;
            grid-size: 1 2;
        }

        #form {
            display: none;
        }

        #add {
            dock: bottom;
            padding-bottom: 1;
        }

        CommandList {
            padding-top: 1;
        }

        #add {
            align: center top;
        }
    """
    
    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit the application"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True, icon="🚀")
        yield ScrollableContainer(
            VerticalScroll(
                CommandList(),
            ),
            Button("Add", id="add", variant="primary"),
            id="sidebar",
        )
        yield VerticalScroll(
            Content(),
            Horizontal(
                Button("Save", id="save", variant="primary"),
                Button("Add Child", id="add-child"),
                Button("Start\n(\"Esc\" to stop)", id="start", variant="success"),
                id="buttons",
            ),
            id="content",
        )
        yield Footer()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Event handler called when a node is selected."""
        text_opening = self.query_one(TextOpening)
        form = self.query_one("#form")
        save_button = self.query_one("#save")
        add_child_button = self.query_one("#add-child")
        if not event.node.data:
            text_opening.styles.display = "block"
            form.styles.display = "none"
            save_button.styles.display = "none"
            add_child_button.styles.display = "none"
        else:
            text_opening.styles.display = "none"
            form.styles.display = "block"
            form.data = event.node.data
            save_button.styles.display = "block"
            add_child_button.styles.display = "none"
            if event.node.data.get("type") == "parent":
                add_child_button.styles.display = "block"
        
    def listen_keys(self) -> None:
        """Listen for key presses."""
        
        for command in self.query_one(CommandList).commands:
            keyboard.add_abbreviation(command['command'], command['text'])
            if command['type'] == 'parent':
                for child in command['children']:
                    keyboard.add_abbreviation(f"{command['command']}{child['command']}", child['text'])
        keyboard.wait('esc')
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "start":
            self.listen_keys()
        elif event.button.id in ["add", "add-child"]:
            form = self.query_one("#form")
            text_opening = self.query_one(TextOpening)
            save_button = self.query_one("#save")
            
            text_opening.styles.display = "none"
            form.styles.display = "block"
            
            if event.button.id == "add-child":
                form.data = {
                    "index": None,
                    "parent": form.data["index"],
                }
            else:
                form.data = {
                    "index": None,
                }
                
            
            save_button.styles.display = "block"
        elif event.button.id == "save":
            form = self.query_one("#form")
            data = form.data
            if data is None:
                return
            
            command_list = self.query_one(CommandList)
            if data.get("index") is not None:
                if data.get("parent") is not None:
                    command_list.commands[data["parent"]]["children"][data["index"]]["name"] = data["name"]
                    command_list.commands[data["parent"]]["children"][data["index"]]["command"] = data["command"]
                    command_list.commands[data["parent"]]["children"][data["index"]]["text"] = data["text"]
                else:
                    command_list.commands[data["index"]]["name"] = data["name"]
                    command_list.commands[data["index"]]["command"] = data["command"]
                    command_list.commands[data["index"]]["text"] = data["text"]
            else:
                new_command = {
                    "name": data["name"],
                    "command": data["command"],
                    "text": data["text"],
                    "type": "parent",
                    "children": [],
                }
                if data.get("parent") is not None:
                    new_command["type"] = "child"
                    command_list.commands[data["parent"]]["children"].append(new_command)
                else:
                    command_list.commands.append(new_command)
            
            with open("commands.json", "w") as file:
                json.dump(command_list.commands, file, indent=2)
                
            # remove CommandList widget
            self.query_one(CommandList).remove()
            # add CommandList widget
            self.query_one("#sidebar").mount(CommandList())
        
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
    
    def action_quit(self) -> None:
        """An action to quit the application."""
        sys.exit()

if __name__ == "__main__":
    app = AutoTypeApp()
    app.run()