from docassemble.webapp.jsonstore import read_answer_json, write_answer_json, JsonStorage, JsonDb
from docassemble.base.generate_key import random_alphanumeric
from docassemble.base.functions import get_current_info
from docassemble.base.util import variables_snapshot_connection
import random

__all__ = ['save_input_data']

def save_input_data(title = '', input_dict = None, tags=None): 
    """
    This function is used by survey type interviews to save input data for data reporting purposes.
    input_dict must be structured like this:
    my_dict['fld_name'] = [fld_name, fld_type as string], e.g. 
    input_fields_dict['event_rating'] = [event_rating, 'radio'] 
    """    
    type_dict = dict()
    field_dict = dict()
    for k, v in input_dict.items():
      type_dict[k] = list(v)[1]
      field_dict[k] = list(v)[0] # Field name without quotes   
    
    data_to_save = dict()
    data_to_save['title'] = title
    data_to_save['field_type_list'] = type_dict # Needed later in process_data
        
    for k, v in type_dict.items():  
      # If a field is of checkboxes type, flatten its elements dict
      # so that each key/value pair is saved in its own column.
      if v in ['checkboxes', 'multiselect']: 
        for subkey, subvalue in field_dict[k].elements.items():
          data_to_save[k + '_' + subkey] = subvalue
      else:
        data_to_save[k] = field_dict[k]

    # Save one record per session to JsonStorage datatable. 
    filename = get_current_info().get('yaml_filename', None)
    random_uid = random_alphanumeric(32)
    new_entry = JsonStorage(filename=filename, key=random_uid, data=data_to_save, tags=tags, persistent=False)
    JsonDb.add(new_entry)
    JsonDb.commit()