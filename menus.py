#!/usr/bin/env python
# encoding: utf-8

import json
import npyscreen, curses
import re
import sys

params_json=json.loads('''{
    "menu-platform": {
        "description": "Platform configuration menu",

        "config-name": {
            "description": "Desired platform",
            "type": "enum",
            "values": ["host", "stm32"]
        },

        "menu-stm32": {
            "description": "STM32 configuration menu",

            "depends_on": "/menu-platform/config-name == 'stm32'",

            "config-device": {
                "type": "enum",
                "values": ["STM32F4", "STM32L4"],
                "description": "Desired device"
            },

            "config-clock": {
                "type": "integer",
                "depends_on": "/menu-platform/menu-stm32/config-device == 'STM32F4'",
                "description": "Desired clock",
                "long_description": "The clock can be configured for STM32F4 device only"
            },

            "config-uart": {
                "type": "array",
                "description": "UART configuration",
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

cfg_json={}

#-------------------------------------------------------------------------------

# Helper routine to get dict value using path
def get_json_val(dict_arg, path):
    val=dict_arg
    for it in path.split('/')[1:]:
        val=val[it]

    return val

# Evaluates "depends" expression
def eval_depends(depends_str):
    try:
        s=re.search('(.*?)\s+(==|!=|>=|<=|>|<)\s+(.*)', depends_str)
        val=get_json_val(cfg_json, s[1])

        # To let string be processed in eval() without errors,
        # it should be captured in quotes
        if type(val) is str:
            val='\'' + val + '\''

        expr=str(val) + s[2] + s[3]
        return eval(expr)
    except:
        return False

#-------------------------------------------------------------------------------

# Navigation widget, button that leads to the given form
class SwitchFormButton(npyscreen.MiniButtonPress):
    def __init__(self, *args, **kwargs):
        self.target_form=kwargs['target_form']
        super().__init__(*args, **kwargs)

    def whenPressed(self):
        self.parent.parentApp.switchForm(self.target_form)

# Creates widget based on parameter type
def create_widget(form, type, param_key, param_obj):
    w=None
    if type == 'enum':
        w=form.add(npyscreen.ComboBox,
                            name=param_obj['description'], values=param_obj['values'],
                            scroll_exit=True)
    elif type == 'integer':
        w=form.add(npyscreen.TitleText, name=param_obj['description'], max_height=1)
    else:
        # Not-yet implemented type
        w=form.add(npyscreen.TitleText, name=param_key, max_height=1)

    if 'depends_on' in param_obj:
        w.hidden=True

    return w

def extract_value(widget, type):
    try:
        if type == 'enum':
            return widget.values[widget.value]
        else:
            return widget.value
    except:
        return widget.value

# Creates form and places navigation button to it
def create_form(app, f_id, name, pf_id, pf_name, params, cfg):
    return app.addForm(f_id, MainForm,
                        name=name, pf_name=pf_name, pf_id=pf_id,
                        my_f_id=f_id, params=params, cfg=cfg)
#-------------------------------------------------------------------------------

class MainForm(npyscreen.ActionFormV2WithMenus):
    def __init__(self, *args, **kwargs):
        # Parent form ID and name, to implement navigation
        self.pf_id=kwargs['pf_id']
        self.pf_name=kwargs['pf_name']
        # Current form ID
        self.my_f_id=kwargs['my_f_id']
        # Parameters object that defines form structure
        self.params_obj=kwargs['params']
        # Configuration object to write data to
        self.cfg_obj=kwargs['cfg']
        # Widget dict
        self.widgets={}

        super().__init__(*args, **kwargs)

    def create(self):
        self.debug=self.add(npyscreen.MultiLineEdit, value='DEBUG', max_height=3)

        # Return to previous form button
        if self.pf_id and self.pf_name:
            self.add(SwitchFormButton,
                name='<<< Back to {}'.format(self.pf_name), target_form=self.pf_id)

        for k, v in self.params_obj.items():
            w=None
            if k.startswith('config-'):
                w=create_widget(self, v['type'], k, v)
                self.widgets[k]=(v, w)
            elif k.startswith('menu-'):
                # Create required JSON subject
                self.cfg_obj[k]={}
                # Create form and handle entering into it
                newF_name=v['description']
                create_form(self.parentApp, k, newF_name, self.my_f_id, self.name, v, self.cfg_obj[k])

                # Go to the child form button
                self.add(SwitchFormButton,
                    name='>>> Enter {}'.format(newF_name), target_form=k)


    def while_editing(self, *args, **keywords):
        for name, data in self.widgets.items():
            if name.startswith('config-'):
                # Place a value into the output configuration JSON
                self.cfg_obj[name]=extract_value(data[1], data[0]['type'])

                # Check if widget should be enabled or not
                if 'depends_on' in data[0]:
                    if eval_depends(data[0]['depends_on']):
                        data[1].hidden=False
                    else:
                        data[1].hidden=True

        self.debug.value=str(self.cfg_obj)
        self.display()
        return


class TestApp2(npyscreen.NPSAppManaged):
    def go_to_menu(self, menu):
        self.switchForm(menu)

    def onStart(self):
        main_f_id="MAIN"
        # Create main form without parent form
        self.main_form=self.addForm(main_f_id, MainForm,
            name="Welcome to theCore", my_f_id=main_f_id, pf_id=None,
            pf_name=None, params=params_json, cfg=cfg_json)

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
#         self.add(npyscreen.TitleText, name="Text:", value= "Press ^T to change screens" )

#         self.add_handlers({"^T": self.change_forms})

#     def on_ok(self):
#         # Exit the application if the OK button is pressed.
#         self.parentApp.switchForm(None)

#     def change_forms(self, *args, **keywords):
#         if self.name == "Screen 1":
#             change_to="SECOND"
#         elif self.name == "Screen 2":
#             change_to="THIRD"
#         else:
#             change_to="MAIN"

#         # Tell the MyTestApp object to change forms.
#         self.parentApp.change_form(change_to)

class TestApp(npyscreen.NPSApp):
    def main(self):

        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        F =npyscreen.Form(name="Welcome to Npyscreen",)
        t =F.add(npyscreen.TitleText, name="Textadasdasdasdasdasdasdasd:",)
        fn=F.add(npyscreen.TitleFilename, name="Filename:")
        fn2=F.add(npyscreen.TitleFilenameCombo, name="Filename2:")
        dt=F.add(npyscreen.TitleDateCombo, name="Date:")
        s =F.add(npyscreen.TitleSlider, out_of=12, name="Slider")
        ml=F.add(npyscreen.MultiLineEdit,
               value="""try typing here!\nMutiline text, press ^R to reformat.\n""",
               max_height=5, rely=9)
        ms=F.add(npyscreen.TitleSelectOne, max_height=4, value=[1,], name="Pick One",
                values=["Option1","Option2","Option3"], scroll_exit=True)
        ms2= F.add(npyscreen.TitleMultiSelect, max_height =-2, value=[1,], name="Pick Several",
                values=["Option1","Option2","Option3"], scroll_exit=True)

        # This lets the user interact with the Form.
        F.edit()


if __name__ == "__main__":
    sys.stdout=open('stdout.log', 'w', 1)

    try:
        App=TestApp2()
        App.run()
    except Exception as e:
        print(e)
        sys.stdout.close()

