from docassemble.base.core import DAObject, DAList, DADict, DAEmpty
from docassemble.base.functions import log, value, comma_and_list, interview_url, showifdef, all_variables
from docassemble.base.util import Individual, Person, Address, DAFileList, DAFile
from docassemble.base.config import daconfig

import requests
import json
__all__= ['LazyFile','LazyFileList','GFLazyFile','GFLazyFileList','MSGraphConnectionObject','get_categories','get_subcategories','get_category_buttons', 'GFEmpty', 'use_default','Tool','ToolList','get_tools', 'space', 'get_answers','add_statistics_row', 'add_statistics_row_gf', 'subcategory_name','category_name', 'get_subcategory_buttons']

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

class LazyFile(DAObject):
    """Represents a reference to a file on the Internet (e.g., SP List). Not downloaded unless manually triggered."""
    def init(self, *pargs, **kwargs):
        super(LazyFile, self).init(*pargs, **kwargs)

    def as_dafile(self, file_obj = None, o365=None):
        """Modify the DAFile file_obj with the contents of the URL and filename in the LazyFile, or if none given, return a new DAFile."""
        if file_obj is None:
            file_obj = DAFile()
            file_obj.initialize(filename=self.filename)
            file_obj.from_url(self.url)
            file_obj.commit()
            return file_obj
        else:
            file_obj.initialize(filename=self.filename)
            file_obj.from_url(self.url)
            file_obj.commit()
        
    def __str__(self):
        return self.filename

    def __unicode__(self):
        return unicode(self.__str__())

class LazyFileList(DAList):
    """List of LazyFiles, which is friendly for drop down list/checkbox selection."""
    def init(self, *pargs, **kwargs):
        super(LazyFileList, self).init(*pargs, **kwargs)
        self.object_type = LazyFile

class GFLazyFile(LazyFile):
    def init(self, *pargs, **kwargs):
        super(GFLazyFile, self).init(*pargs, **kwargs)
        
    def as_dafile(self, file_obj = None, o365=None):
        """Modify the DAFile file_obj with the contents of the URL and filename in the LazyFile, or if none given, return a new DAFile."""
        if o365:
          o365.refresh_download_link(self)
        if file_obj is None:
            file_obj = DAFile()
            file_obj.title = self.primaryTitle()
            file_obj.initialize(filename=self.filename)
            file_obj.from_url(self.url)
            file_obj.commit()
            return file_obj
        else:
            file_obj.initialize(filename=self.filename)
            file_obj.title = self.primaryTitle()            
            file_obj.from_url(self.url)
            file_obj.commit()

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
        
class GFLazyFileList(DAList):
    """List of LazyFiles, with Gorrissen SharePoint extensions."""
    def init(self, *pargs, **kwargs):
        super(GFLazyFileList, self).init(*pargs, **kwargs)
        self.object_type = GFLazyFile
    
    def in_category(self,category_id, check_access=False, user=None):
      return [form for form in self.elements if hasattr(form, 'fields') and category_id == form.fields.get('CategoryLookupId')] or DAList(there_are_any=False)
    
    def in_category_not_subcategory(self, category_id, check_access=False, user=None):
      filtered = [form for form in self.elements if hasattr(form, 'fields') and (form.fields.get('CategoryLookupId') == category_id) and (not form.fields.get('SubcategoryLookupId')) ]
      if len(filtered):
        return filtered
      else:
        return DAList(there_are_any=False)       
          
    def in_subcategory(self,subcategory_id, check_access=False, user=None):
      return [form for form in self.elements if hasattr(form,'fields') and form.fields.get('SubcategoryLookupId',False) and form.fields.get('SubcategoryLookupId') == subcategory_id] or DAList(there_are_any=False)
    
class MSGraphConnectionObject(DAObject):
    """Creates a connection object that can be used to access resources with the Microsoft Graph API with application-level credentials.
    Only a few limited API calls are implemented. Use the Docassemble config options microsoft graph: tenant id, client id, and client secret
    or specify tenant_id, client_id, and client_secret as arguments to the class constructor."""

    def init(self, *pargs, **kwargs):
        super(MSGraphConnectionObject, self).init(*pargs, **kwargs)

        # Default to using Docassemble configuration to retrieve credentials to connect to Microsoft Graph
        #
        if not hasattr(self, 'tenant_id'):
            tenant_id = daconfig.get('microsoft graph', {}).get('tenant id')
        else:
            tenant_id = self.tenant_id

        if not hasattr(self, 'client_id'):
            client_id = daconfig.get('microsoft graph', {}).get('client id')
        else:
            client_id = self.client_id

        if not hasattr(self, 'client_secret'):
            client_secret = daconfig.get(
                'microsoft graph', {}).get('client secret')
        else:
            client_secret = self.client_secret

        if not hasattr(self, 'default_site'):
            self.default_site = daconfig.get('microsoft graph', {}).get('default site')

        token_url = "https://login.microsoftonline.com/" + tenant_id + "/oauth2/v2.0/token"

        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        r = requests.post(token_url, data=token_data)
        self.token = r.json()['access_token']

        self.authorization_header = {
            "Authorization": "Bearer " + self.token
        }

    def get_request(self, url, top=100):
        """ Return JSON parsed data for the given URL. Handles using authorization header automatically. Doesn't handle pagination yet but you can specify results limit by changing the value of top.
        Defaults to returning 100 results. Up to 1000 could be returned without pagination."""
        # params = {}
        params = {
            '$top': top
        }
        return (requests.get(url, headers=self.authorization_header, params=params)).json()

    def refresh_download_link(self,lazyfile):
      """Get a new download URL for the specified DriveItem"""
      res = self.get_request(lazyfile.requestURL)
      if res:
        if res.get('@microsoft.graph.downloadUrl'):
          lazyfile.url = res.get('@microsoft.graph.downloadUrl')


    def get_user(self, upn, who=None):
        """Will replace attributes from the given Individual object with user information from Microsoft Graph request. Returns raw JSON results
        if no Individual object is passed in the keyword argument 'who' """
        user_url = "https://graph.microsoft.com/v1.0/users/" + upn
        user_url += "?$select=givenName,surname,mail,businessPhones,otherMails,department,jobTitle,streetAddress,city,state,postalCode,faxNumber,employeeId"
        # drq = requests.get(user_url, headers=self.authorization_header)
        # res = drq.json()

        # Unimplemented: get a photo for the user
        # "https://graph.microsoft.com/v1.0/users/qsteenhuis@gbls.org/photo" # ("@odata.mediaContentType": "image/jpeg")
        # "https://graph.microsoft.com/v1.0/users/qsteenhuis@gbls.org/photo/$value"
        # open('headshot.jpg', 'wb').write(r.content)

        res = self.get_request(user_url)

        if who is None:
            return res
        else:
            who.name.first = res.get('givenName')
            who.name.last = res.get('surname')
            who.email = res.get('mail')
            who.otherMails = res.get('otherMails')
            who.department = res.get('department')
            who.address.address = res.get('streetAddress')
            who.address.city = res.get('city')
            who.address.state = res.get('state')
            who.address.zip = res.get('postalCode')
            # if isinstance(res.get('businessPhones', None), list):
            who.phone_number = next(iter(res.get('businessPhones', [])), None)
            who.fax_number = res.get('faxNumber')
            who.phone = who.phone_number # backwards compatibility
            who.employeeId = res.get('employeeId')
            who.jobTitle = res.get('jobTitle')

    def get_simple_items_in_list(self, site, list_id=None):
        """Can be used to retrieve custom metadata on files when list ID is a for a drive"""
        # 'https://graph.microsoft.com/v1.0/sites/gorrissenfederspiel.sharepoint.com:/sites/Docassemble:/lists/39c81862-a7e0-47b1-8674-951ce89b4570/items?expand=fields'
        
        # NOTE: the etag property of a list item seems to be the same as the etag property of the drive item it maps onto.
        # However: the case is different! Not sure this is guaranteed to be the same.
        # Filename does seem to be unique across folder

        list_items_url = "https://graph.microsoft.com/v1.0/sites/" + \
                site + ":/lists/" + list_id + "/items"
        res = self.get_request(list_items_url)

        items = res.get('value',[])

        return items


    def get_items_in_list(self, site=None, list_id=None, list_name=None):
        """Can be used to retrieve custom metadata on files when list ID is a for a drive"""
        # 'https://graph.microsoft.com/v1.0/sites/gorrissenfederspiel.sharepoint.com:/sites/Docassemble:/lists/39c81862-a7e0-47b1-8674-951ce89b4570/items?expand=fields'
        
        # NOTE: the etag property of a list item seems to be the same as the etag property of the drive item it maps onto.
        # However: the case is different! Not sure this is guaranteed to be the same.
        # Filename does seem to be unique across folder
        # https://graph.microsoft.com/v1.0/sites/ + site + :/lists/ + list_name + /items?expand=columns,driveItem,items(expand=fields)

        if site is None:
            site = self.default_site
        
        if list_id is None:
            site_id = self.get_site_id(site)
            list_id = self.get_list_id(site_id,list_name)

        list_items_url = "https://graph.microsoft.com/v1.0/sites/" + \
                site + ":/lists/" + list_id + "/items?expand=fields"
        res = self.get_request(list_items_url)

        items = res.get('value',[])

        return items


    def get_drive_items_with_metadata(self, site, drive_name, lazylist = None):
        """Get a list containing all files in a drive, along with any custom columns/metadata available in the list facet of the drive."""
        #site_id = self.get_site_id(site)
        #list_id = self.get_list_id(site_id, drive_name)
        #list_items = self.get_items_in_list(site, list_id)
        drive_id = self.get_drive_id(site, drive_name)
        drive_items = self.get_files_in_folder(site, drive_id=drive_id, lazylist=lazylist, get_list_metadata=True)

        # Question: it seems list items and drive items are returned with the same ordering. Is this guaranteed? '"{C1ABE511-76DF-4150-B285-E79301725F4D},1"'
        # TODO: Maybe we can at least start list search with same index
        #for index, item in enumerate(drive_items):
        #    if len(list_items) > index: # length starts at 1, index is zero based
        #        # If the filenames match, add the list item metadata to the file object
        #        for list_item in list_items:
        #            if item.filename == list_item.get('fields',{}).get('FileLeafRef'):
        #                item.fields = list_item.get('fields',{})
        #                continue

        return drive_items


    # We don't need this--we can use the get_list_id method, since a drive is just a list
    # def get_list_id_for_drive(self, drive):
    #     """Get the list ID for a drive"""
        
    #     # 'https://graph.microsoft.com/v1.0/drives/{drive-id}/list'
    #     pass

    def get_site_id(self, site=None):
        # TODO: cleanup variable naming convention. site vs subsite vs drive above
        # See: https://docs.microsoft.com/en-us/graph/api/resources/site?view=graph-rest-beta#id-property
        """ Specify site like this: gblsma.sharepoint.com:/sites/SiteName (note the :)
        see: https://docs.microsoft.com/en-us/graph/api/site-get"""
        # example request URL: https://graph.microsoft.com/v1.0/sites/gorrissenfederspiel.sharepoint.com:/sites/Docassemble
        

        if site is None:
            site = self.default_site

        site_id_url = "https://graph.microsoft.com/v1.0/sites/"
        site_id_url += site
        res = self.get_request(site_id_url)
        
        site_id = res.get('id','')
        site_id = site_id.split(',')

        if len(site_id) == 3:
            return site_id[1] # the ID we need is the second element in a comma-separated string

        return "Not found"

    def get_list_id(self, siteID, list_name):
        """We need a siteID, which is second part of the `id` attribute of a site"""
        list_id_url = "https://graph.microsoft.com/v1.0/sites/"
        list_id_url += siteID + "/lists"
        res = self.get_request(list_id_url)

        lists = res.get('value',{})
        for list in lists:
            if list.get('name') == list_name:
                return list.get('id')
        
        return "Not found"
    
    def get_files_in_folder(self, site=None, drive=None, folder=None, lazylist=None, drive_id=None, get_list_metadata=False, enabled_only=True, docx_only=True):
        """ List all files in the specified site and drive, with an optional folder path. Files will include a Filename, URL to download the file, and a method to return a DAFile."""
        if drive_id is None:
            drive_id = self.get_drive_id(site, drive)

        if drive_id is None:
            return None

        # https://graph.microsoft.com/v1.0/drives/b!0PCobezqK0ecoB7I0TbTJkvMrGm2K-VIuGS2szEGq6BiGMg54KexR4Z0lRzom0Vw/root:/SubFolderTest:/children?expand=listItem
        if folder is None:
            folder_url = "https://graph.microsoft.com/v1.0/drives/" + \
                drive_id + "/root/children"
        else:
            folder_url = "https://graph.microsoft.com/v1.0/drives/" + \
                drive_id + '/root:/' + folder + ':/children'

        if get_list_metadata:
            folder_url += "?expand=listItem"

        log(folder_url)                
        res = self.get_request(folder_url)

        items = res.get('value')

        if lazylist is None:
            files = GFLazyFileList()
        else:
            files = lazylist

        files.auto_gather = False
        item_request_url = "https://graph.microsoft.com/v1.0/drives/"
        item_request_url += drive_id + "/items/"
        for item in items:
            if get_list_metadata and enabled_only and item.get('listItem',{}).get('fields',{}).get('Enabled') == False:
              continue
            # https://docs.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0&tabs=http
            # /drives/{drive-id}/items/{item-id}/content
            if docx_only and item.get('file',{}).get('mimeType') != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
              continue
            if item.get('file'):
                files.there_are_any = True
                my_file = files.appendObject()
                my_file.id = item.get('id')
                my_file.requestURL = item_request_url + my_file.id
                my_file.url = item.get('@microsoft.graph.downloadUrl')
                my_file.filename = item.get('name')
                if get_list_metadata:
                    tmplistitem = item.get('listItem', {})
                    my_file.fields = tmplistitem.get('fields',{})
                # files.append(my_file)
        files.gathered = True
        return files

    def get_folders_in_folder(self, site, drive=None, drive_id=None, folder=None):
        """List all subfolders in the given path."""
        if drive_id is None:
            drive_id = self.get_drive_id(site, drive)

        if drive_id is None:
            return None

        if folder is None:
            folder_url = "https://graph.microsoft.com/v1.0/drives/" + \
                drive_id + "/root/children"
        else:
            folder_url = "https://graph.microsoft.com/v1.0/drives/" + \
                drive_id + '/root:/' + folder + ':/children'
        res = self.get_request(folder_url)

        items = res.get('value')

        folders = list()
        for item in items:
            if item.get('folder'):
                folders.append(item.get('name'))

        return folders

    def get_drive_id(self, site=None, drive_name="Templates"):
        """ Specify site like this: gblsma.sharepoint.com:/Units/Immigration"""
        if site is None:
            site = self.default_site

        drive_id_url = "https://graph.microsoft.com/v1.0/sites/"
        drive_id_url += site + ":/drives"
        res = self.get_request(drive_id_url)

        drives = res.get('value')

        if drives is not None:
            for drive in drives:
                if drive.get('name') == drive_name:
                    return drive.get('id')
            # return res
        return None



    def get_contacts(self, upn, default_address='home'):
        """ Return a list of contacts from the given user's Universal Principal Name (i.e., username@domain.org for most organizations, or username@org.onmicrosoft.com).
        Does not paginate--will return the first 100 contacts only for now. You can choose whether to default to 'home' or 'business' address and phone."""
        contacts_url = "https://graph.microsoft.com/v1.0/users/" + upn + "/contacts"

        res = self.get_request(contacts_url)

        people = DAList(object_type=Individual,
                        auto_gather=False, gathered=True)

        for p_res in res.get('value', []):

            person = people.appendObject()
            person.name.first = p_res.get('givenName', '')
            person.name.last = p_res.get('surname', '')
            if p_res.get('middleName'):
                person.name.middle = p_res.get('middleName')
            person.jobTitle = p_res.get('jobTitle')
            person.title = p_res.get('title')

            person.business_phones = p_res.get('businessPhones', [])
            person.home_phones = p_res.get('homePhones', [])
            person.mobile_number = p_res.get('mobilePhone')

            person.initializeAttribute('home_address', Address)
            person.home_address.address = p_res.get(
                'homeAddress', {}).get('street')
            person.home_address.city = p_res.get('homeAddress', {}).get('city')
            person.home_address.state = p_res.get(
                'homeAddress', {}).get('state')
            person.home_address.zip = p_res.get(
                'homeAddress', {}).get('postalCode')
            # if not p_res.get('homeAddress',{}).get('countryOrRegion') is None:
            #    person.home_address.country = p_res.get('homeAddress',{}).get('countryOrRegion')

            person.initializeAttribute('business_address', Address)
            person.business_address.address = p_res.get(
                'businessAddress', {}).get('street')
            person.business_address.city = p_res.get(
                'businessAddress', {}).get('city')
            person.business_address.state = p_res.get(
                'businessAddress', {}).get('state')
            person.business_address.zip = p_res.get(
                'businessAddress', {}).get('postalCode')
            # if not p_res.get('businessAddress',{}).get('countryOrRegion') is None:
            #    person.business_address.country = p_res.get('businessAddress',{}).get('countryOrRegion')

            person.emails = p_res.get('emailAddresses', [])

            if p_res.get('emailAddresses'):
                person.email = next(iter(person.emails), []).get(
                    'address', None)  # take the first email

            # Try to respect the address kind the user wants, but if not present, use the address we have (which might be null)
            # Information is often put in the business phone/address fields if the contact only has one address/phone
            if default_address == 'home':
                if p_res.get('homeAddress'):
                    person.address = person.home_address
                else:
                    person.address = person.business_address
            else:
                if p_res.get('businessAddress'):
                    person.address = person.business_address
                else:
                    person.address = person.home_address

            if default_address == 'home':
                if p_res.get('homePhones'):
                    # just take the first home phone in the list
                    person.phone_number = next(iter(person.home_phones), '')
                else:
                    person.phone_number = next(
                        iter(person.business_phones), '')
            else:
                if p_res.get('businessPhones'):
                    # just take the first business phone
                    person.phone_number = next(
                        iter(person.business_phones), '')
                else:
                    person.phone_number = next(iter(person.home_phones), '')

        return people

    def create_list_entry(self, site_id, list_id, data_dict):
        """Create a new list record at the specified site and list IDs."""
        new_item_url = "https://graph.microsoft.com/v1.0/sites/" + \
            site_id + "/lists/" + list_id + "/items"
        
        return self.post_request(new_item_url, data_dict)
    
    def post_request(self, url, data_dict):
        """Send JSON formatted data to the specified graph API url. Return json response if successful."""
        return (requests.post(url, headers=self.authorization_header, json=data_dict)).json()

def get_categories(o365, site=None, category_list_name="Categories", enabled_only=True, check_access=False, user=None, always_allow='gorrissenfederspiel.com'):
    """Get a list of categories from Gorrissen Federspiel
    SharePoint site"""
    site_id = o365.get_site_id(site)
    category_list_id = o365.get_list_id(site_id, category_list_name)
    category_list_results = o365.get_items_in_list(site, category_list_id)
    category_dict = {}

    subcategories = get_subcategories(o365, site, check_access=check_access, user=user, always_allow=always_allow)
    #subcategories.sort(key=lambda y: y.get('SortOrder',0))

    user_domain = user.split("@")[1].lower() if (user and len(user.split("@"))>1) else None

    for item in category_list_results:
        # flatten to capture just the lookup value for each oranization domain listed
        orgs = [org.get('LookupValue').lower() for org in item.get('fields',{}).get('Organizations_x003a_Domain',[]) if len(org) > 1]
        user_list = [y.lower() for y in item.get('fields',{}).get('Users','').split(',') if y]
        # or user in user_list
        if enabled_only and item.get('fields',{}).get('Enabled') == False:
          continue
        elif check_access and not ((user and user.lower() in user_list) or user_domain == always_allow or user_domain in orgs):
          continue
        else:
          category_dict[item.get('id')] = {
              'id': item.get('id'),
              'Title': item.get('fields',{}).get('Title'),
              'Title_Da': item.get('fields',{}).get('Title_Da'),
              'icon': item.get('fields',{}).get('icon'),
              'SortOrder': item.get('fields',{}).get('SortOrder0'), # It's hard to rename a SharePoint column
              'Enabled': item.get('fields',{}).get('Enabled'),
              'Folder': item.get('fields',{}).get('Folder', "Templates"),
              'Organizations': orgs,
              'Users': user_list,
              'fields': item.get('fields')
          }
          if enabled_only:
            category_dict[item.get('id')]['subcategories'] = [c for c in subcategories if c.get('Parent Category') == item.get('id') and c.get('Enabled') == True]
          else:
            category_dict[item.get('id')]['subcategories'] = [c for c in subcategories if c.get('Parent Category') == item.get('id')]
    # category_dict.sort(key=lambda y: y.get('SortOrder',0))
    return category_dict

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
  
def get_subcategories(o365, site=None, subcategory_list_name="Subcategories", check_access=False, user=None, always_allow="gorrissenfederspiel.com"):
    """Get a list of subcategories from Gorrissen Federspiel
    SharePoint site. This is all the subcategories; not matched up to a specific category"""
    site_id = o365.get_site_id(site)
    category_list_id = o365.get_list_id(site_id, subcategory_list_name)
    category_list_results = o365.get_items_in_list(site, category_list_id)
    category_list = []

    user_domain = user.split("@")[1].lower() if (user and len(user.split("@"))>1) else None

    for item in category_list_results:
        orgs = [org.get('LookupValue').lower() for org in item.get('fields',{}).get('Organizations_x003a_Domain',[]) if len(org) > 1]
        user_list = [y.lower() for y in item.get('fields',{}).get('Users','').split(',') if y]

        if check_access and not ((user and user.lower() in user_list) or user_domain == always_allow or user_domain in orgs):
          continue
        else:
          category_list.append( {
              'id': item.get('id'),
              'Title': item.get('fields',{}).get('Title'),
              'Title_Da': item.get('fields',{}).get('Title_Da'),
              'Parent Category': item.get('fields',{}).get('Parent_x0020_CategoryLookupId'),
              'icon': item.get('fields',{}).get('icon'),
              'SortOrder': item.get('fields',{}).get('SortOrder'),
              'Enabled': item.get('fields',{}).get('Enabled'),
              'Folder': item.get('fields',{}).get('Folder', "Templates"),
              'Organizations': orgs,
              'Users': user_list,
          })

    return category_list  
  
def subcategory_name(id, subcategories=None, o365=None, language='en'):
  if not subcategories:
    subcategories = get_subcategories(o365)
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
        return self.filter(category_id = category_id)
        # return [form for form in self.elements if hasattr(form, 'fields') and category_id == form.fields.get('CategoryLookupId')] or DAList(there_are_any=False)

    def in_category_not_subcategory(self, category_id):
        return [tool for tool in self.elements if tool.category_id == category_id and not hasattr(tool, 'subcategory_id')]
        # [form for form in self.elements if hasattr(form, 'fields') and (form.fields.get('CategoryLookupId') == category_id) and (not form.fields.get('SubcategoryLookupId')) ]
    
    def in_subcategory(self, subcategory_id):
        return [tool for tool in self.elements if hasattr(tool, 'subcategory_id') and tool.subcategory_id == subcategory_id]

    def __str__(self):
        return comma_and_list([tool.show() for tool in self.elements])

class Tool(DAObject):
    """category_id, subcategory_id, title, title_da, interview_url"""
    def __str__(self):
        return self.title
    
    def show(self,language='en'):
        if language=='da':
            return '<a href="' + interview_url(i=self.interview_url) +'">' + self.title_da + "</a>"
        else:
            return '<a href="' + interview_url(i=self.interview_url) +'">' + self.title + "</a>"


def get_tools(o365, site, list_name="Tools", intrinsicName=''):
    """Return a list of tools. Specify intrinsicName."""
    site_id = o365.get_site_id(site)
    list_id = o365.get_list_id(site_id, list_name)

    tool_response = o365.get_items_in_list(site, list_id)

    tools = ToolList(intrinsicName, auto_gather=False)
    
    for result in tool_response:
        tool = tools.appendObject()
        tool.id = result.get('id')
        tool.title = result.get('fields',{}).get('Title')
        tool.title_da = result.get('fields',{}).get('Title_Da')
        tool.interview_url = result.get('fields',{}).get('InterviewURL')        
        tool.category_id = result.get('fields',{}).get('CategoryLookupId')
        tool.subcategory_id = result.get('fields',{}).get('SubcategoryLookupId')

    tools.gathered = True

    return tools


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

if __name__ == '__main__':
  #microsoft graph:
  #tenant id: x
  #client id: x
  #client secret: xB
  o365 = MSGraphConnectionObject(tenant_id="x",client_id="x",client_secret="x")
  folders = DADict.using(object_type=LazyFileList, auto_gather=False)
  drive_contents = GFLazyFileList.using(auto_gather=False,gathered=True)

  site = "gorrissenfederspiel.sharepoint.com:/sites/Docassemble"
  site_id = o365.get_site_id(site)
  template_list_id = o365.get_list_id(site_id, "Templates")
  template_list_contents = o365.get_items_in_list(site, template_list_id)
  
  o365.get_drive_items_with_metadata(site, "Templates") #, drive_contents)
  
  category_list_id = o365.get_list_id(site_id, "Subcategories")
  category_list_contents = o365.get_items_in_list(site, category_list_id) 
  
  categories = get_categories(o365, site)
  
  print("test")