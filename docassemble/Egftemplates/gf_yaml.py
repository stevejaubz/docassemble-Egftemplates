from docassemble.base.util import DAObject, DAList, DADict, DAEmpty, Individual, Person, Address, DAFileList, DAFile, DAStaticFile, path_and_mimetype, log, value, comma_and_list, interview_url, showifdef, all_variables
from docassemble.base.config import daconfig
import ruamel.yaml as yaml

import requests
import json
#__all__= ['GFLazyFile','GFLazyFileList','MSGraphConnectionObject','get_categories','get_subcategories','get_category_buttons', 'GFEmpty', 'use_default','Tool','ToolList','get_tools', 'space', 'get_answers','add_statistics_row', 'add_statistics_row_gf', 'subcategory_name','category_name', 'get_subcategory_buttons']

def use_default(variable, default):
  """Return either the variable value, or a default value, depending on value of global variable
  use_default_values"""
  if use_default_values:
    return default
  else:
    return value(variable)

class GFEmpty(DAEmpty):
    def init(self, *pargs, **kwargs):
        super(GFEmpty, self).init(*pargs, **kwargs)
        if not hasattr(self, 'placeholder_value'):
            self.placeholder_value = '[X]'
        
    def __str__(self):
        return '[          ]'
        # return self.placeholder_value

    def __call__(self, *pargs, **kwargs):
        return GFEmpty()      

    def __getitem__(self, index):
        return GFEmpty()      

class GFYamlLoader(DAObject):
    """
    Implements Gorrissen template API with YAML files instead of SharePoint.
    """
    def init(self, *pargs, **kwargs):
        super(GFYamlLoader, self).init(*pargs, **kwargs)
        if not hasattr(self, 'path'):
            self.path = 'docassemble.GFYaml:data/sources/'
        # else: # not sure this would be helpful
        #    if not self.path.endswith('/'):
        #        self.path += '/'
        if not hasattr(self, 'categories'):
            self.categories = 'categories.yml'
        if not hasattr(self, 'subcategories'):
            self.subcategories = 'subcategories.yml'
        if not hasattr(self, 'templates'):
            self.templates = 'templates.yml'
        if not hasattr(self, 'tools'):
            self.tools = 'tools.yml'

    def get_categories(self, enabled_only=True, check_access=False, user=None, always_allow='gorrissenfederspiel.com'):
        """
        Sample entry with expected dictionary keys: (based on export from SharePoint)
        -
            ID: 11
            Title: Insolvency
            icon: columns
            Title_Da: Konkurs
            SortOrder: 11
            Enabled: True
            'Organizations:Domain': "gorrissenfederspiel.com;mydomain.com"
            Users: ""
        It is okay to add more fields (and some are present) but they are not used.
        """
        yaml_results = self.__load_yaml(self.categories)
        # return yaml_results
        category_dict = {}
        subcategories = self.get_subcategories(check_access=check_access, user=user, always_allow=always_allow, enabled_only=enabled_only)
        for item in yaml_results:
            id = str(item.get('ID'))
            orgs = []
            user_list = [y.lower() for y in item.get('Users','').split(';') if y]
            if item.get('Organizations:Domain'):
                orgs = [y.lower() for y in item.get('Organizations:Domain').split(';') if y]
            if enabled_only and item.get('Enabled') == False:
                continue
            elif check_access and not ((user and user.lower() in user_list) or user_domain == always_allow or user_domain in orgs):
                continue
            else:
                category_dict[id] = {
                    'id': id,
                    'Title': item.get('Title'),
                    'Title_Da': item.get('Title_Da'),
                    'icon': item.get('icon'),
                    'SortOrder': item.get('SortOrder'),
                    'Enabled': item.get('Enabled'),
                    'Organizations': orgs,
                    'Users': item.get('Users'),
                    'fields': item,
                    # 'Folder': looks like Folder was never used
                    # 'Fields': Don't think we need to reconstruct a 'fields' dictionary
                }
            if enabled_only:
                category_dict[id]['subcategories'] = [c for c in subcategories if c.get('Parent Category') == id and c.get('Enabled') == True]
            else:
                category_dict[id]['subcategories'] = [c for c in subcategories if c.get('Parent Category') == id]

        return category_dict
    
    def get_subcategories(self, check_access=False, user=None, always_allow="gorrissenfederspiel.com", enabled_only=True):
        yaml_results = self.__load_yaml(self.subcategories)
        subcategory_list = []
        for item in yaml_results:
            id = str(item.get('ID'))
            orgs = []
            user_list = [y.lower() for y in item.get('Users','').split(';') if y]
            if item.get('Organizations:Domain'):
                orgs = [y.lower() for y in item.get('Organizations:Domain').split(';') if y]
            if enabled_only and item.get('Enabled') == False:
                continue
            elif check_access and not ((user and user.lower() in user_list) or user_domain == always_allow or user_domain in orgs):
                continue
            else:
                subcategory_list.append({
                    'id': id,
                    'Title': item.get('Title'),
                    'Title_Da': item.get('Title_Da'),
                    'Parent Category': str(item.get('Parent Category:ID')),
                    'icon': item.get('icon'),
                    'SortOrder': item.get('SortOrder'),
                    'Enabled': item.get('Enabled'),
                    'Organizations': orgs,
                    'Users': item.get('Users'),
                    'fields': item,
                    # 'Folder': looks like Folder was never used
                    # 'Fields': Don't think we need to reconstruct a 'fields' dictionary
                })
        return subcategory_list
    
    def get_tools(self, intrinsicName=''):
        tool_results = self.__load_yaml(self.tools)

        tools = ToolList(intrinsicName, auto_gather=False)

        for item in tool_results:
            tool = tools.appendObject()
            tool.title = item.get('Title')
            tool.title_da = item.get('Title_Da')
            tool.interview_url = item.get('InterviewURL')        
            tool.category_id = item.get('Category')
            tool.subcategory_id = item.get('Subcategory')
        tools.gathered=True
        return tools
            
    def get_files_in_folder(self, site=None, drive=None, folder=None, lazylist=None, drive_id=None, get_list_metadata=False, enabled_only=True, docx_only=True):
        """
        Method signature just to be compatible with gf_graph.py.
        Only arguments that are used are docx_only, enabled_only, and lazylist
        """
        template_results = self.__load_yaml(self.templates)
        # return template_results

        if lazylist is None:
            files = GFYamlFileList(auto_gather=False)
        else:
            files = lazylist
            files.auto_gather=False # Disable autogathering even if someone provides a list

        for item in template_results:
            # Note: the YAML exported from SharePoint uses Danish language for column labels
            if enabled_only and item.get('Enabled') == False:
              continue
            if docx_only and (not item.get('Navn','').endswith('.docx')):
              continue
            # files.there_are_any = True # this is probably not necessary, leaving for compatibility
            new_document = files.appendObject()
            new_document.filename = item.get('Navn')
            new_document.fields = item
        files.gathered = True
        return files
    # def get

    def __load_yaml(self, yaml_file_name, default=[]):
        path = path_and_mimetype(self.path + yaml_file_name)[0]
        #try:
        with open(path, encoding="utf-8") as file:
          results = yaml.safe_load(file)
          return results or default
        #except:
        #    log("Unable to open YAML file " + str(path))
        #    return default

class GFYamlFile(DAFile):
    def init(self, *pargs, **kwargs):
        super(GFYamlFile, self).init(*pargs, **kwargs)
        
    def as_dafile(self, package_path="data/templates/", o365=None):
        """Modify the DAFile file_obj with the contents of the URL and filename in the LazyFile, or if none given, return a new DAFile."""
        # if file_obj is None:
        file_obj = DAStaticFile(filename=package_path + self.filename)
        file_obj.title = self.primaryTitle()
        return file_obj
        # else:
        #     file_obj.filename=self.filename
        #     file_obj.title = self.primaryTitle()            
        #     file_obj.from_url(self.url)
        #     file_obj.commit()

    def primaryTitle(self):
      if self.fields.get('PrimaryLanguage') == 'da':
        if self.fields.get('Title_da'):
          return self.fields.get('Title_da')
      elif self.fields.get('Title'):
        return self.fields.get('Title')
      return self.filename
    
    def description(self):
      return self.fields.get('LongDescription','')
    
    def description_new_line(self):
      if self.description():
        return '[BR]' + self.description()
      else:
        return ''
      
    def __str__(self):
        titles = []
        if hasattr(self, 'fields') and self.fields.get('PrimaryLanguage'):
          # Prioritize language order by primary language
          if self.fields.get('PrimaryLanguage') == 'da':
            if self.fields.get('Title_da'):
              titles.append( self.fields.get('Title_da'))
            if self.fields.get('Title'):
              titles.append( self.fields.get('Title'))
          else:
            if self.fields.get('Title'):
              titles.append(self.fields.get('Title'))
            if self.fields.get('Title_da'):
              titles.append(self.fields.get('Title_da'))
        if len(titles) == 2:
          title =  titles[0] + ' (' + titles[1] + ')'
        elif len(titles) == 1:
          title = titles[0]
        else:
          title = self.filename
        return (title + (' _' + self.fields.get('PrimaryLanguage','') + '_' if self.fields.get('PrimaryLanguage') else '')).strip()


class GFYamlFileList(DAList):
    """List of LazyFiles, with Gorrissen YAML extensions."""
    def init(self, *pargs, **kwargs):
        super(GFYamlFileList, self).init(*pargs, **kwargs)
        self.object_type = GFYamlFile
    
    def in_category(self,category_id, check_access=False, user=None):
      return [form for form in self.elements if hasattr(form, 'fields') and str(category_id) == str(form.fields.get('Category:ID'))] or DAList(there_are_any=False)
    
    def in_category_not_subcategory(self, category_id, check_access=False, user=None):
      filtered = [form for form in self.elements if hasattr(form, 'fields') and (str(form.fields.get('Category:ID')) == str(category_id)) and (not form.fields.get('Subcategory:ID')) ]
      if len(filtered):
        return filtered
      else:
        return DAList(there_are_any=False)       
          
    def in_subcategory(self,subcategory_id, check_access=False, user=None):
      return [form for form in self.elements if hasattr(form,'fields') and form.fields.get('Subcategory:ID',False) and str(form.fields.get('Subcategory:ID')) == str(subcategory_id)] or DAList(there_are_any=False)

def get_categories(yaml_obj, site=None, category_list_name="Categories", enabled_only=True, check_access=False, user=None, always_allow='gorrissenfederspiel.com'):
    """Get a list of categories from Gorrissen Federspiel
    SharePoint site"""
    return yaml_obj.get_categories(enabled_only=enabled_only, check_access=check_access, user=user, always_allow=always_allow)

def get_category_buttons(category_dict, language='en'):
  """Get code for docassemble buttons, sorted by SortOrder"""
  category_list = sorted(category_dict.values(), key=lambda y: y.get("SortOrder") )
  if language == 'en':
    return [{category['id']: category['Title'], "image": category['icon']} for category in category_list]
  else:
    return [{category['id']: category['Title_Da'], "image": category['icon']} for category in category_list]

def get_subcategory_buttons(categories, category, language='en'):
  """  
  
  """
  return [{category['id']: category['Title'], "image": category['icon']} for category in categories[category].get('subcategories')] if language == 'en' else [{category['id']: category.get('Title_Da',category.get('Title')), "image": category['icon']} for category in categories[category].get('subcategories')]  
  
def get_subcategories(yamlobj, site=None, subcategory_list_name="Subcategories", check_access=False, user=None, always_allow="gorrissenfederspiel.com"):
    """Get a list of subcategories from Gorrissen Federspiel
    YAML. This is all the subcategories; not matched up to a specific category"""
    return yamlobj.get_subcategories(check_access=check_access, user=user, always_allow=always_allow)
  
def subcategory_name(id, subcategories=None, o365=None, language='en'):
  if not subcategories:
    subcategories = o365.get_subcategories()
  for item in subcategories:
    if item.get('id') == id:
      if language == 'en' and item.get('Title'):
        return item.get('Title')
      else:
        return item.get('Title_Da')
  return id

def category_name(id, categories=None, o365=None, language='en'):
  if not categories:
    categories = get_categories(o365)    
  item =  categories.get(id,{})
  if not item:
    return id
  if language == 'en' and item.get('Title'):
    return item.get('Title')
  else:
    return item.get('Title_Da')

class ToolList(DAList):
    def init(self, *pargs, **kwargs):
        super(ToolList, self).init(*pargs, **kwargs)
        self.object_type=Tool
    
    def in_category(self, category_id):
        return [tool for tool in self.elements if str(tool.category_id) == str(category_id)]
        # return [form for form in self.elements if hasattr(form, 'fields') and category_id == form.fields.get('CategoryLookupId')] or DAList(there_are_any=False)

    def in_category_not_subcategory(self, category_id):
        return [tool for tool in self.elements if str(tool.category_id) == str(category_id) and not hasattr(tool, 'subcategory_id')]
        # [form for form in self.elements if hasattr(form, 'fields') and (form.fields.get('CategoryLookupId') == category_id) and (not form.fields.get('SubcategoryLookupId')) ]
    
    def in_subcategory(self, subcategory_id):
        return [tool for tool in self.elements if hasattr(tool, 'subcategory_id') and str(tool.subcategory_id) == str(subcategory_id)]

    def __str__(self):
        return comma_and_list([tool.show() for tool in self.elements])

class Tool(DAObject):
    """category_id, subcategory_id, title, title_da, interview_url"""
    def __str__(self):
        return self.title
    
    def show(self,language='en'):
        if language=='da':
            return '<a href="' + interview_url(i=self.interview_url) +'"  target="_blank">' + self.title_da + "</a>"
        else:
            return '<a href="' + interview_url(i=self.interview_url) +'"  target="_blank">' + self.title + "</a>"


def get_tools(yaml_obj, site, list_name="Tools", intrinsicName=''):
    """Return a list of tools. Specify intrinsicName."""
    return yaml_obj.get_tools(intrinsicName=intrinsicName)


def space(var_name, prefix=' ', suffix=''):
  """If the value as a string is defined, return it prefixed/suffixed. Defaults to prefix 
  of a space. Helps build a sentence with less cruft. Equivalent to SPACE function in 
  HotDocs."""
  if defined(var_name):
    return prefix + showifdef(var_name) + suffix
  else:
    return ''

def add_statistics_row_gf(o365, site, list_name, session_id, organization, user_id, document_title, answers, site_id = None, list_id=None):
    columns = {
        "SessionID": session_id,
        "Organization": organization,
        "User": user_id,
        "Title": document_title,
        "Answers": get_answers()
    }
    return add_statistics_row(o365, site, list_name=list_name, columns=columns, site_id=site_id, list_id=list_id)

def add_statistics_row(o365, site, list_name="InterviewStatistics", columns={}, site_id=None, list_id=None):
    site_id = site_id or o365.get_site_id(site)
    list_id = list_id or o365.get_list_id(site_id, list_name)
    return o365.create_list_entry(site_id, list_id, data_dict=columns)

def get_answers(mapping = {},skip=[],custom=False):
    """
    Light wrapper on the built-in all_variables() function that strips out some sensitive or redundant fields.
    Optionally: provide a mapping to re-map keys, skip additional fields, and use a different variable
    set than that provided by all_variables.
    """

    keys_to_ignore = ['_internal',
                        'url_args',
                        'PY2',
                        'string_types',
                        'nav',
                        '__warningregistry__',
                        'CONVERTER_CLASSES', 
                        'CONVERTES_TYPES',
                        'categories', 
                        'drive_contents',
                        'o365'] + skip

    if custom:
        interview_state = custom
    else:
        interview_state = all_variables(simplify=False)
    interview_state = {k:v for k, v in interview_state.items() if k not in keys_to_ignore}

    mapped = {}
    if len(mapping) > 0:
        for name, value in interview_state.items():
            if name in mapping:
                mapped[mapping[name]] = value
            else:
                mapped[name] = value
        return mapped
    else:
        return interview_state