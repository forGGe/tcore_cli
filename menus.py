#!/usr/bin/env python
# encoding: utf-8

import json
import npyscreen, curses
import re
import sys

params_json = json.loads('''{
    "menu-platform": {
        "help": "Platform configuration menu",

        "config-name": {
            "help": "Desired platform",
            "type": "enum",
            "values": ["host", "stm32"]
        },

        "menu-stm32": {
            "help": "STM32 configuration menu",

            "depends_on": "/menu-platform/config-name == 'stm32'",

            "config-device": {
                "type": "enum",
                "values": ["STM32F4", "STM32L4"],
                "help": "Desired device"
            },

            "config-clock": {
                "type": "integer",
                "depends_on": "/menu-platform/menu-stm32/config-device == 'STM32F4'",
                "help": "Desired clock, supported only by STM32F4"
            },

            "config-uart": {
                "type": "array",
                "help": "UART configuration",
                "key": "config-channel",
                "items": {
                    "config-channel": {
                        "type": "string",
                        "pattern": "^US?ART\\\d$"
                    },
                    "config-baud": {
                        "type": "integer",
                        "default": 115200
                    },
                    "config-alias": {
                        "type": "string"
                    },
                    "config-comment": {
                        "type": "string"
                    }
                }
            }
        }
    }
}''')

cfg_json = {}

# Helper routine to get dict value using path
def get_json_val(dict_arg, path):
    val = dict_arg
    for it in path.split('/'):
        val = val[it]

    return val

# Evaluates "depends" expression
def eval_depends(depends_str):
    try:
        s = re.search('(.*?)(==)(.*)', depends_str)
        val = get_json_val(cfg_json, s[1])
        return eval(val + str(val) + ' == ' + s[2])
    except:
        return False

class SwitchFormButton(npyscreen.MiniButtonPress):
    def __init__(self, *args, **kwargs):
        self.target_form = kwargs['target_form']
        super().__init__(*args, **kwargs)

    def whenPressed(self):
        self.parent.parentApp.switchForm(self.target_form)

class MainForm(npyscreen.ActionForm):
    def __init__(self, *args, **kwargs):
        # Parent form ID and name, to implement navigation
        self.pf_id = kwargs['pf_id']
        self.pf_name = kwargs['pf_name']
        # Current form ID
        self.my_f_id = kwargs['my_f_id']
        # Parameters object that defines form structure
        self.params_obj = kwargs['params']
        # Configuration object to write data to
        self.cfg_obj = kwargs['cfg']
        # Widget dict
        self.widgets = {}

        super().__init__(*args, **kwargs)

    def create(self):
        self.debug = self.add(npyscreen.MultiLineEdit, value = 'DEBUG', max_height=3)

        # Return to previous form button
        if self.pf_id and self.pf_name:
            self.add(SwitchFormButton,
                name = '<<< Back to {}'.format(self.pf_name), target_form = self.pf_id)

        for k, v in self.params_obj.items():
            w = None
            if k.startswith('config-'):
                # Display configuration value and prepare configuration field
                if v['type'] == 'enum':
                    w = self.add(npyscreen.TitleSelectOne,
                            name = v['help'], values = v['values'], max_height = 3,
                            scroll_exit=True)
                elif v['type'] == 'integer':
                    w = self.add(npyscreen.TitleText, name = v['help'])
                else:
                    w = self.add(npyscreen.TitleText, name = k)

                if 'depends_on' in v: # and not eval_depends(v['depends_on']):
                    w.hidden = True

            elif k.startswith('menu-'):
                # Create required JSON subject
                self.cfg_obj[k] = {}
                # Create form and handle entering into it
                newF_name = v['help']
                self.parentApp.addForm(k, MainForm,
                    name = newF_name, pf_name = self.name, pf_id = self.my_f_id,
                    my_f_id = k, params = v, cfg = self.cfg_obj[k])

                # Go to the child form button
                self.add(SwitchFormButton,
                    name = '>>> Enter {}'.format(newF_name), target_form = k)

            self.widgets[k] = (v, w)

    def while_editing(self, *args, **keywords):
        for name, data in self.widgets.items():
            if name.startswith('config-'):
                self.cfg_obj[name] = data[1].value

        self.debug.value = str(self.cfg_obj)
        self.DISPLAY()
        return


class TestApp2(npyscreen.NPSAppManaged):
    def go_to_menu(self, menu):
        self.switchForm(menu)

    # def process_menu(self, F, F_id, menu, current_cfg):

    #     for k, v in menu.items():

    #         if k.startswith('config-'):
    #             # Display configuration value
    #             if v['type'] == 'enum':
    #                 F.add(npyscreen.TitleSelectOne,
    #                     name = v['help'], values = v['values'], max_height = 3, scroll_exit=True)
    #         elif k.startswith('menu-'):
    #             # Create menu and handle entering into it
    #             newF_name = v['help']
    #             newF = self.addForm(k, MainForm, name = newF_name)

    #             # Go to the menu button
    #             F.add(SwitchFormButton,
    #                 name = '>>> Enter {}'.format(newF_name), target_form = k)

    #             # Return from the menu button
    #             newF.add(SwitchFormButton,
    #                 name = '<<< Back to {}'.format(F.name), target_form = F_id)

    #             self.process_menu(newF, k, v, cfg_json)

    def onStart(self):
        main_f_id = "MAIN"
        # Create main form without parent form
        self.main_form = self.addForm(main_f_id, MainForm,
            name = "Welcome to theCore", my_f_id = main_f_id, pf_id = None,
            pf_name = None, params = params_json, cfg = cfg_json)

        # self.process_menu(F, main_f_id, params_json, cfg_json)

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")



# class MyTestApp(npyscreen.NPSAppManaged):
#     def onStart(self):
#         # When Application starts, set up the Forms that will be used.
#         # These two forms are persistent between each edit.
#         self.addForm("MAIN",       MainForm, name="Screen 1", color="IMPORTANT",)
#         self.addForm("SECOND",     MainForm, name="Screen 2", color="WARNING",  )
#         # This one will be re-created each time it is edited.
#         self.addFormClass("THIRD", MainForm, name="Screen 3", color="CRITICAL",)

#     def onCleanExit(self):
#         npyscreen.notify_wait("Goodbye!")

#     def change_form(self, name):
#         # Switch forms.  NB. Do *not* call the .edit() method directly (which
#         # would lead to a memory leak and ultimately a recursion error).
#         # Instead, use the method .switchForm to change forms.
#         self.switchForm(name)

#         # By default the application keeps track of every form visited.
#         # There's no harm in this, but we don't need it so:
#         self.resetHistory()

# class MainForm(npyscreen.ActionForm):
#     def create(self):
#         self.add(npyscreen.TitleText, name = "Text:", value= "Press ^T to change screens" )

#         self.add_handlers({"^T": self.change_forms})

#     def on_ok(self):
#         # Exit the application if the OK button is pressed.
#         self.parentApp.switchForm(None)

#     def change_forms(self, *args, **keywords):
#         if self.name == "Screen 1":
#             change_to = "SECOND"
#         elif self.name == "Screen 2":
#             change_to = "THIRD"
#         else:
#             change_to = "MAIN"

#         # Tell the MyTestApp object to change forms.
#         self.parentApp.change_form(change_to)

class TestApp(npyscreen.NPSApp):
    def main(self):
        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        F  = npyscreen.Form(name = "Welcome to Npyscreen",)
        t  = F.add(npyscreen.TitleText, name = "Textadasdasdasdasdasdasdasd:",)
        fn = F.add(npyscreen.TitleFilename, name = "Filename:")
        fn2 = F.add(npyscreen.TitleFilenameCombo, name="Filename2:")
        dt = F.add(npyscreen.TitleDateCombo, name = "Date:")
        s  = F.add(npyscreen.TitleSlider, out_of=12, name = "Slider")
        ml = F.add(npyscreen.MultiLineEdit,
               value = """try typing here!\nMutiline text, press ^R to reformat.\n""",
               max_height=5, rely=9)
        ms = F.add(npyscreen.TitleSelectOne, max_height=4, value = [1,], name="Pick One",
                values = ["Option1","Option2","Option3"], scroll_exit=True)
        ms2= F.add(npyscreen.TitleMultiSelect, max_height =-2, value = [1,], name="Pick Several",
                values = ["Option1","Option2","Option3"], scroll_exit=True)

        # This lets the user interact with the Form.
        F.edit()


if __name__ == "__main__":
    App = TestApp2()
    App.run()
