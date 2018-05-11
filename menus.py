#!/usr/bin/env python
# encoding: utf-8

import json
import npyscreen, curses
import re
import sys
import abc

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
                "description": "Desired device1"
            },
            "config-device2": {
                "type": "enum",
                "values": ["STM32F4", "STM32L4"],
                "description": "Desired device2"
            },
            "config-device3": {
                "type": "enum",
                "values": ["STM32F4", "STM32L4"],
                "description": "Desired device3"
            },
            "config-device44": {
                "type": "enum",
                "values": ["STM32F4", "STM32L4"],
                "description": "Desired device4"
            },

            "config-clock": {
                "type": "integer",
                "depends_on": "/menu-platform/menu-stm32/config-device == 'STM32F4'",
                "description": "Desired clock",
                "long_description": "The clock can be configured for STM32F4 device only"
            },

            "config-uart": {
                "type": "table",
                "description": "UART configuration",
                "key": "config-channel",
                "items": {
                    "config-channel": {
                        "type": "enum",
                        "values": [ "UART0", "UART1", "UART2" ]
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

#-------------------------------------------------------------------------------

class abstract_ui(abc.ABC):
    @abc.abstractmethod
    def set_engine(self, engine):
        pass

    @abc.abstractmethod
    def create_menu(self, menu_id):
        pass

    @abc.abstractmethod
    def delete_menu(self, menu_id):
        pass

    @abc.abstractmethod
    def create_config(self, menu_id, id, type, description, long_description=None, **kwargs):
        pass

    @abc.abstractmethod
    def delete_config(self, menu_id, id):
        pass


class engine:
    def __init__(self, ui_instance):
        self.ui_instance = ui_instance
        self.items_data = {}
        self.config_params = params_json
        self.output_cfg = cfg_json

        # Root form must be named as 'MAIN'
        root_menu_id = 'MAIN'
        self.ui_instance.set_engine(self)
        self.ui_instance.create_menu(None, root_menu_id, 'Welcome to theCore configurator')
        self.process_menu(None, root_menu_id, self.config_params, self.output_cfg)

    def on_config_change(self, menu_id, id, **kwargs):
        for k, v in self.items_data.items():
            if k == id and v['item_type'] == 'config' and menu_id == v['menu']:
                # Store value
                normalized_cfg_name = v['name']
                v['container'][normalized_cfg_name] = kwargs['value']
                break

        # Re-calculate and update menu accordingly

        p_menu = self.items_data[menu_id]['p_menu']
        menu_params = self.items_data[menu_id]['data']
        normalized_name = self.items_data[menu_id]['name']
        output_obj = self.items_data[menu_id]['container'][normalized_name]

        self.process_menu(p_menu, menu_id, menu_params, output_obj)
        return

    # Processes menu, creating and deleting configurations when needed
    def process_menu(self, p_menu_id, menu_id, menu_params, output_obj):
        # Internal helper to find item by normalized key
        def is_created(name):
            for k, v in self.items_data.items():
                if v['name'] == name:
                    return True

            return False

        for k, v in menu_params.items():
            if not k.startswith('config-') and not k.startswith('menu-'):
                continue # Skip not interested fields

            # Possible ways to handle items
            create_item = 0
            skip_item = 1
            delete_item = 2

            decision = None

            # Is item has a dependency?
            if 'depends_on' in v:
                # Is dependency satisfied?
                if self.eval_depends(v['depends_on']):
                    # Is item created?
                    if is_created(k):
                        # item is already created, nothing to do
                        decision = skip_item
                    else:
                        # New item should be created
                        decision = create_item
                else:
                    # Dependency is not satisfied - item shouldn't
                    # be displayed.

                    # Is item created?
                    if is_created(k):
                        # Item must be deleted, if present.
                        decision = delete_item
                    else:
                        # No item present, nothing to delete
                        decision = skip_item
            else:
                # Item is dependless. Meaning should be displayed
                # no matter what.

                # Is item created?
                if is_created(k):
                    # item is already created, nothing to do
                    decision = skip_item
                else:
                    # New item should be created
                    decision = create_item

            if k.startswith('config-'):
                # Create, skip, delete config

                if decision == create_item:
                    type = v['type']

                    # Initialize empty config, later UI will publish
                    # changes to it
                    output_obj[k] = {}

                    # No backslash at the end means it is a config
                    new_config_id = menu_id + '/' + k

                    self.items_data[new_config_id] = {
                        'item_type': 'config',
                        'name': k,
                        'data': v,
                        'p_menu': p_menu_id,
                        'menu': menu_id,
                        'container': output_obj
                    }

                    if type == 'enum':
                        self.ui_instance.create_config(menu_id, new_config_id,
                            'enum', description=v['description'],
                            values=v['values'])
                    elif type == 'integer':
                        self.ui_instance.create_config(menu_id, new_config_id,
                            'integer', description=v['description'])

                elif decision == delete_item:
                    # Configuration must be deleted, if present.
                    self.ui_instance.delete_config(menu_id, k)
                    output_obj.pop(k, None)
                    self.items_data.pop(k, None)

                elif decision == skip_item:
                    pass # Nothing to do

            elif k.startswith('menu-'):
                # Create, skip, delete menu
                if decision == create_item:
                    new_menu_id = menu_id + '/' + k + '/'
                    self.ui_instance.create_menu(menu_id, new_menu_id,
                        description=v['description'])

                    output_obj[k] = {}
                    self.items_data[new_menu_id] = {
                        'item_type': 'menu',
                        'name': k,
                        'data': v,
                        'p_menu': menu_id,
                        'container': output_obj
                    }

                    self.process_menu(menu_id, new_menu_id, v, output_obj[k])

                elif decision == delete_item:
                    # Delete menu first
                    target_menu_id = menu_id + '/' + k + '/'
                    target_container = self.items_data[target_menu_id]['container']
                    target_container.pop(k, None)

                    self.ui_instance.delete_menu(target_menu_id)
                    self.items_data.pop(target_menu_id, None)

                    # TODO: sanitize menus (challenge: root menu don't have p_menu_id)

                    # Sanitize all configs: delete configuration without menu
                    to_delete = [ item_id for item_id, item_v in self.items_data.items() \
                        if item_v['item_type'] == 'config' and not item_v['menu'] in self.items_data ]
                    for k in to_delete:
                        del self.items_data[k]


                elif decision == skip_item:
                    pass # Nothing to do

    # Helper routine to get dict value using path
    def get_json_val(self, dict_arg, path):
        val=dict_arg
        for it in path.split('/')[1:]:
            val=val[it]

        return val

    # Evaluates "depends" expression
    def eval_depends(self, depends_str):
        try:
            s=re.search(r'(.*?)\s+(==|!=|>=|<=|>|<)\s+(.*)', depends_str)
            val=self.get_json_val(self.output_cfg, s[1])

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
class switch_form_btn(npyscreen.MiniButtonPress):
    def __init__(self, *args, **kwargs):
        self.target_form=kwargs['target_form']
        super().__init__(*args, **kwargs)

    def whenPressed(self):
        self.parent.parentApp.switchForm(self.target_form)

class npyscreen_switch_form_option(npyscreen.OptionFreeText):
    def __init__(self, *args, **kwargs):
        self.target_form=kwargs['target_form']
        self.app=kwargs['app']
        kwargs.pop('target_form', None)
        kwargs.pop('app', None)
        super().__init__(*args, **kwargs)

    def change_option(self):
        self.app.switchForm(self.target_form)

class npyscreen_multiline(npyscreen.MultiLineAction):
    def __init__(self, *args, **kwargs):
        self.ui=kwargs['ui']
        self.f_id=kwargs['f_id']
        super().__init__(*args, **kwargs)

    def actionHighlighted(self, act_on_this, key_press):
        self.ui.on_item_selected(self.f_id, act_on_this)

class npyscreen_form(npyscreen.ActionFormV2WithMenus):
    def __init__(self, *args, **kwargs):
        self.my_f_id = kwargs['my_f_id']
        self.ui = kwargs['ui']

        super().__init__(*args, **kwargs)

    def create(self):
        pass

    def adjust_widgets(self, *args, **keywords):
        self.ui.check_widgets(self.my_f_id)

class npyscreen_ui(abstract_ui):
    def __init__(self, npyscreen_app):
        self.menu_forms = {}
        self.npyscreen_app = npyscreen_app
        self.engine = None

    def set_engine(self, engine):
        self.engine = engine

    def create_menu(self, p_menu_id, menu_id, description, long_description=None):
        f = self.npyscreen_app.addForm(menu_id, npyscreen_form,
            name=description, my_f_id=menu_id, ui=self)

        ms = f.add(npyscreen.OptionListDisplay, name="Option List",
                values = npyscreen.OptionList().options,
                scroll_exit=True,
                max_height=5)

        self.menu_forms[menu_id] = { 'parent': p_menu_id, 'form': f, 'config_widget': ms }
        # Empty configuration dict, will be populated in create_config() function
        self.menu_forms[menu_id]['config_fields'] = {}
        self.menu_forms[menu_id]['nav_link'] = []

        if p_menu_id:
            self.menu_forms[p_menu_id]['nav_link'].append(
                npyscreen_switch_form_option(target_form=menu_id,
                    name='>>> Go to ', value=menu_id, app=f.parentApp),
            )

            # self.menu_forms[p_menu_id]['nav_link'].append(
            #     npyscreen.OptionFreeText('FreeText', value='', documentation="This is some documentation.")
            # )

            self.menu_forms[menu_id]['nav_link'] = [
                npyscreen_switch_form_option(target_form=p_menu_id,
                    name='<<< Back to ', value=p_menu_id, app=f.parentApp),
            ]

    def delete_menu(self, menu_id):
        # Delete all links to this form
        for f_id, f_data in self.menu_forms.items():
            f_data['nav_link'] = \
                [ nav for nav in f_data['nav_link'] if nav.target_form != menu_id ]

        self.npyscreen_app.removeForm(menu_id)

    def create_config(self, menu_id, id, type, description, long_description=None, **kwargs):
        self.menu_forms[menu_id]['config_fields'][id] = {
            'form': menu_id,
            'type': type,
            'description': description,
            'long_description': long_description,
            'last_value': ''
        }

        if type == 'enum':
            self.menu_forms[menu_id]['config_fields'][id]['option'] = \
                npyscreen.OptionSingleChoice(description, choices=kwargs['values'])
        else:
            self.menu_forms[menu_id]['config_fields'][id]['option'] = \
                npyscreen.OptionFreeText(description)

        self.update_form(menu_id)

    def delete_config(self, menu_id, id):
        self.menu_forms[menu_id]['config_fields'].pop(id, None)
        self.update_form(menu_id)

    ''' Private method, updates form '''
    def update_form(self, f_id):
        Options = npyscreen.OptionList()
        options = Options.options

        for id, data in self.menu_forms[f_id]['config_fields'].items():
            options.append(data['option'])

        for link in self.menu_forms[f_id]['nav_link']:
            options.append(link)

        self.menu_forms[f_id]['config_widget'].values = options

        # This method is heavy, but redraws entire screen without glitching
        # option list itself (as .display() does)
        self.menu_forms[f_id]['form'].DISPLAY()

    ''' Private method, checks if there are any updates on form widgets '''
    def check_widgets(self, f_id):
        fields = self.menu_forms[f_id]['config_fields']

        for id, data in fields.items():
            if data['last_value'] != data['option'].value:
                data['last_value'] = data['option'].value
                # Report one config at a time
                value=data['option'].value
                if data['type'] == 'enum':
                    # Normalize a value
                    value=value[0]
                self.engine.on_config_change(f_id, id, value=value)
                return

        self.update_form(f_id)

    ''' Private method, catches event from user '''
    def on_item_selected(self, f_id, act_on_this):
        fields = self.menu_forms[f_id]['config_fields']

        field_id = None

        for id, data in fields.items():
            if data['description'] == act_on_this:
                field_id = id

        npyscreen.notify_ok_cancel('Hello ', title="Message", form_color='STANDOUT')







#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------

class theCoreConfiguratorApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.ui = npyscreen_ui(self)
        self.engine = engine(self.ui)

#-------------------------------------------------------------------------------


class MyTestApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.registerForm("MAIN", MyMainForm())

class MyMainForm(npyscreen.FormWithMenus):
    def create(self):
        self.add(npyscreen.TitleText, name = "Text:", value= "Just some text." )
        self.how_exited_handers[npyscreen.wgwidget.EXITED_ESCAPE]  = self.exit_application

        # The menus are created here.
        self.m1 = self.add_menu(name="Main Menu", shortcut="^M")
        self.m1.addItemsFromList([
            ("Display Text", self.whenDisplayText, None, None, ("some text",)),
            ("Just Beep",   self.whenJustBeep, "e"),
            ("Exit Application", self.exit_application, "é"),
        ])

        self.m2 = self.add_menu(name="Another Menu", shortcut="b",)
        self.m2.addItemsFromList([
            ("Just Beep",   self.whenJustBeep),
        ])

        self.m3 = self.m2.addNewSubmenu("A sub menu", "^F")
        self.m3.addItemsFromList([
            ("Just Beep",   self.whenJustBeep),
        ])

    def whenDisplayText(self, argument):
       npyscreen.notify_confirm(argument)

    def whenJustBeep(self):
        curses.beep()

    def exit_application(self):
        curses.beep()
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.switchFormNow()

class MyMulti(npyscreen.MultiLineAction):
    def actionHighlighted(self, act_on_this, key_press):
        self.parent.ch = act_on_this

class MyMainFormTest(npyscreen.FormWithMenus):
    def create(self):
        self.ch = '<<<>>>'
        self.f = self.add(npyscreen.TitleFixedText, name = "Fixed Text:" , value="This is fixed text")
        t = self.add(npyscreen.TitleText, name = "Text:", )
        p = self.add(npyscreen.TitlePassword, name = "Password:")
        fn = self.add(npyscreen.TitleFilename, name = "Filename:")
        dt = self.add(npyscreen.TitleDateCombo, name = "Date:")
        cb = self.add(npyscreen.Checkbox, name = "A Checkbox")
        s = self.add(npyscreen.TitleSlider, out_of=12, name = "Slider")
        self.ml= self.add(MyMulti,
            values = [ 'try typing here!', 'Mutiline text, press ^R to reformat',  'nPress ^X for automatically created list of menus' ],
            max_height=5, rely=9)
        ms= self.add(npyscreen.TitleSelectOne, max_height=4, value = [1,], name="Pick One",
                values = ["Option1","Option2","Option3"], scroll_exit=True, width=30)
        ms2= self.add(npyscreen.MultiSelect, max_height=4, value = [1,],
                values = ["Option1","Option2","Option3"], scroll_exit=True, width=20)

        bn = self.add(npyscreen.MiniButton, name = "Button",)

        #gd = self.add(npyscreen.SimpleGrid, relx = 42, rely=15, width=20)
        gd = self.add(npyscreen.GridColTitles, relx = 42, rely=15, width=20, col_titles = ['1','2','3','4'])
        gd.values = []
        for x in range(36):
            row = []
            for y in range(x, x+36):
                row.append(y)
            gd.values.append(row)


    # This lets the user play with the Form.
    def while_editing(self, *args, **keywords):
        self.f.value = self.ch

class TestApp(npyscreen.NPSAppManaged):
    def onStart(self):
        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        F = MyMainFormTest(name = "Welcome to Npyscreen",)
        self.registerForm("MAIN", F)

class TestAppz(npyscreen.NPSApp):
    def main(self):
        Options = npyscreen.OptionList()

        # just for convenience so we don't have to keep writing Options.options
        options = Options.options

        options.append(npyscreen.OptionFreeText('FreeText', value='', documentation="This is some documentation."))
        options.append(npyscreen.OptionMultiChoice('Multichoice', choices=['Choice 1', 'Choice 2', 'Choice 3']))
        options.append(npyscreen.OptionFilename('Filename', ))
        options.append(npyscreen.OptionDate('Date', ))
        options.append(npyscreen.OptionMultiFreeText('Multiline Text', value=''))
        options.append(npyscreen.OptionMultiFreeList('Multiline List'))

        try:
            Options.reload_from_file('/tmp/test')
        except FileNotFoundError:
            pass

        F  = npyscreen.Form(name = "Welcome to Npyscreen",)

        ms = F.add(npyscreen.OptionListDisplay, name="Option List",
                values = options,
                scroll_exit=True,
                max_height=None)

        F.edit()

        Options.write_to_file('/tmp/test')

if __name__ == "__main__":
    with open('stdout.log', 'w', 1) as fd:
        sys.stdout=fd
        App=theCoreConfiguratorApp()
        App.run()

