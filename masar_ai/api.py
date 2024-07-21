import frappe
import requests
import json
from frappe import utils
def get_currency():
    currency = "JOD"
    return currency
def cohere_api_key_and_url(message , web_search ):
    api_key = "hEi9R5FjRb8WIsCUfclH8MqyyzLzevFdd90q1gDy"
    url = "https://api.cohere.ai/v1/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "command-r-plus",
        "message": message,
        "temperature": 0.3,
        "chat_history": [],
        "prompt_truncation": "auto", 
    }
    if web_search == 1:
        data["connectors"] = [{"id":"web-search"}]
    return  url , headers , data 


def base_request_data():
    base_url =  'http://147.182.251.32:8000/api/resource'
    headers = {
        "Authorization": "Basic NDNlNjY0ZTk4MjJmZDFjOjBlN2FiOTljNzBhNmE1OQ==",
        "Content-Type": "application/json"
    }
    return base_url , headers

@frappe.whitelist()   
def generate_response_message(user_message):
    system_message = '''
          Please extract the retailer shop order from the message below, analyze the data accurately, and format it into JSON as follows:
            {
                "session_id":,
                "session_duration_elapsed_time":,
                "tokens_per_input": ,
                "tokens_per_output": ,
                "total_session_input_tokens": ,
                "total_session_output_tokens":,
                "response_time":,
                "order": {
                    "supplier": ,
                    "items": [
                        {
                            "item": (in English),
                            "description": ,
                            "qty": (float value),
                            "commonly_known_as": (in Arabic),
                            "category": ,
                            "subcategory": ,
                            "variance":,
                            "basic_measuring_unit":,
                            "package_measuring_unit": ,
                            "brand":,
                            "price_range": { 
                                "min": (float value), 
                                "max": (float value),
                                "avg": (float value) 
                            } in '''+get_currency()+'''
                        }
                    ]
                }
            }

            The message is:'''
    message = system_message + user_message
    url , headers , data  = cohere_api_key_and_url(message , web_search= 1 )
    response = requests.post(url, headers=headers, json=data)
    try:
        if response.status_code == 200:
            response_json = response.json()
            response_text = response_json["text"]
            json_response = (response_text.split("```json"))[1].split("```")[0]
            return json_response
    except Exception as e:
        return("Error:",str(e))



@frappe.whitelist()
def create_po(company , supplier , ai_json):
    base_url , headers = base_request_data()
    data_ai = validate_json_text(ai_json)
    items = data_ai['order']['items']
    get_supplier_json = data_ai['order']['supplier']
    supplier_json = get_supplier( supplier_json= get_supplier_json)
    if supplier_json:
        supplier_po = supplier_json
    else: 
        supplier_po = supplier
    po_items = []
    for item in items:
        item_code = proccess_search_items(item["item"] , item["item"])
        if item_code:
            item_code_po = item_code
        else :
            item_code_from_description =  validate_item_description(item_code)
            if item_code_from_description:
                item_code_po = item_code_from_description
            else : 
                item_code_from_commonly_knwon_name = search_in_commonly_known_names(item["item"] , item["commonly_known_as"])
                if item_code_from_commonly_knwon_name : 
                    item_code_po = item_code_from_commonly_knwon_name
                else: 
                   item_code_from_commonly_knwon = search_in_commonly_known_names(item["commonly_known_as"] , item["item"]) 
                   if item_code_from_commonly_knwon: 
                       item_code_po = item_code_from_commonly_knwon
        if item_code_po is None:
            frappe.throw(f'There is no item {item["item"]}')
        uom = get_uom_item( item_code_po, item["basic_measuring_unit"])
        qty = qty = float(item["qty"])
        rate = float(get_item_rate(item_code_po, uom))
        dict_item = {
            "item_code":item_code_po,
            "schedule_date": str(utils.today()),
            "qty": qty,
            "uom": uom,
            "rate": rate,
            "amount": rate * qty,
            "warehouse": "Stores - KCSCD",
        }
        po_items.append(dict_item)
    url = base_url + f'/Purchase Order'
    if not url and headers:
        frappe.throw('No credentials')
    data = {
        "doctype": "Purchase Order ",
        "naming_series": "PUR-ORD-.YYYY.-",
        "title": supplier_po,
        "supplier": supplier_po,
        "transaction_date": str(utils.today()),
        "currency": get_currency(),
        "company": company,
        "docstatus": 0,
        "items": po_items
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()



@frappe.whitelist()
def proccess_search_items(item_code, item_name):
    try:
        if item_code and item_name:
            json_item_code = item_code.replace(" ", "")
            json_item_name = item_name.replace(" ", "")

            data_items = frappe.db.sql(""" SELECT item_code, item_name FROM `tabItem`""", as_dict = True)
            if data_items and data_items[0]:
                for item_dict in data_items:
                    if json_item_code == item_dict["item_code"]:
                        return json_item_code
                    elif json_item_name == item_dict["item_name"] or json_item_name in item_dict["item_name"]:
                        return item_dict["item_code"]
                else:
                    return False
        else:
            return False
    except Exception as e:
        return f"Exception Proccess Search Items Error:  {str(e)}"
@frappe.whitelist()
def validate_item_description(item_code):
    try:
        if not isinstance(item_code, str):
            return False
        
        all_items_in_sql = frappe.db.sql(f"""SELECT name, description FROM `tabItem`""", as_dict=True)
        
        if all_items_in_sql:
            for item_info in all_items_in_sql:
                data_item_code = item_info.name
                description = item_info.description
                if description and item_code in description:
                    return data_item_code
            return False
        else:
            return False
    except Exception as e:
        return f"Exception Validate Item Description Error: {str(e)}"



@frappe.whitelist()
def search_in_commonly_known_names(item_name , commonly_known_as ):
    try:
        doc_name = 'Commonly Known'
        item_name_without_spaces = item_name.replace(' ', '')
        all_commonly_knwon_sql = frappe.db.sql(f"""SELECT  name , document , commonly_known FROM `tab{doc_name}`""" , as_dict = True)
        if all_commonly_knwon_sql and all_commonly_knwon_sql[0]:
            #### check commonly known as
            for all_commonly_knwon in all_commonly_knwon_sql:
                #### Read data for item
                commonly_known_name = all_commonly_knwon.name
                commonly_known_item = all_commonly_knwon.document
                commonly_known_data = all_commonly_knwon.commonly_known
                commonly_known_data_without_spaces = commonly_known_data.replace(' ' ,'')
                if commonly_known_item and commonly_known_data:
                    if item_name_without_spaces in commonly_known_data_without_spaces:
                        ## the item is exist but in other name
                        try:
                            if commonly_known_as not in commonly_known_data_without_spaces:
                                new_commonly_known_data = commonly_known_data + '\n' + commonly_known_as
                                try:
                                    frappe.db.set_value(f'{doc_name}', f'{commonly_known_name}', 'commonly_known', new_commonly_known_data+'\n'+'-')
                                except Exception as e:
                                    return f'Exception: There are Error in Request :{e}'
                            else:
                                pass
                        except Exception as e:
                            return f'Exception: There are Error in Commonly Known: {e}'
                        return commonly_known_item
        return False
    except Exception as e :
        return f'Exception Search In Commonly Known Names: Error: {e}'
def validate_json_text(json_text):
    try: 
        _json = json.loads(json_text)
        return _json
    except Exception as e : 
        message = f'The json file has Error. edit it to be in correct json format: {json_text}'
        url , headers , data  = cohere_api_key_and_url(message  , web_search= 0)
        response = requests.post(url, headers=headers, json=data)
        response_json = response.json()
        response_text = response_json["text"]
        json_response = (response_text.split("```json"))[1].split("```")[0]
        return validate_json_text(json_response)

@frappe.whitelist()
def generate_commonly_known(dynamic_doc):
    message = f'''قم بإعطاء الكلمات المرادفة لكلمة ({dynamic_doc})  بكل اللهجات بالمفرد و الجمع بدون حركات اعرابية , as json Format: 
            {str("""```json{
                 "arabic" : [option_one , option_two , .... ]
                 }```""")}
            '''   
    url , headers , data = cohere_api_key_and_url(message  , web_search= 0)
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    response_text = response_json["text"]
    json_data = (response_text.split("```json"))[1].split("```")[0]
    json_text = validate_json_text(json_data)
    arabic_words = json_text["arabic"]
    commonly_known = ''
    for arabic_word in list(arabic_words):
        commonly_known += arabic_word +'\n'+'-'
    message = f'''Give the words that are synonymous with the word ({dynamic_doc}) in all dialects, in the singular and plural in english  , as json Format:
            {str("""```json{
                 "english" : [option_one , option_two , .... ]
                 }```""")}
            '''   
    url , headers , data = cohere_api_key_and_url(message  , web_search= 0)
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    response_text = response_json["text"]
    json_data = (response_text.split("```json"))[1].split("```")[0]
    json_text = validate_json_text(json_data)
    english_words = json_text["english"]
    for english_word in list(english_words):
        commonly_known+= english_word +'\n'+'-'
    return commonly_known

@frappe.whitelist()
def get_supplier(supplier_json = None):
    base_url, headers = base_request_data()
    supplier_list = []

    try:    
        if supplier_json in [None , "" , " "]:
            return False
        response = requests.get(base_url + '/Supplier', headers=headers)
        response_json =  response.json()
        data_json = response_json["data"]
        
        for supplier in data_json:
            supplier_list.append(supplier['name'])
    
        for supplier in supplier_list:
            if supplier == supplier_json or supplier in supplier_json:
                return supplier 
        return False
        
    except Exception as e:
        return f" Exception Validate supplier Error: {str(e)} "




def get_uom_item( item_code , uom):

    uoms_sys = frappe.db.sql("SELECT name FROM `tabUOM`" , as_dict = True)
    for uom_sys in uoms_sys:
        if uom == uom_sys.name:
            return uom_sys.name
    uom_without_spaces = uom.replace(" " , "")
    doc_name = 'Commonly Known'
    all_commonly_knwon_sql = frappe.db.sql(f"""SELECT document , commonly_known FROM `tab{doc_name}`""" , as_dict = True)
    if all_commonly_knwon_sql and all_commonly_knwon_sql[0]:
            for all_commonly_knwon in all_commonly_knwon_sql:
                commonly_known_uom = all_commonly_knwon.document
                commonly_known_data = all_commonly_knwon.commonly_known
                commonly_known_data_without_spaces = commonly_known_data.replace(' ' ,'')
                if uom_without_spaces in commonly_known_data_without_spaces:
                            return commonly_known_uom
            

    default_item_uom = frappe.db.sql(""" SELECT stock_uom FROM `tabItem` WHERE item_code = %s """ , (item_code), as_dict = True )
    if default_item_uom and default_item_uom[0] and default_item_uom[0]['stock_uom']:
                return default_item_uom[0]['stock_uom']
    


def get_item_rate(item_code, uom):
    try:
        item_rate = frappe.db.sql("""
            SELECT price_list_rate 
            FROM `tabItem Price`
            WHERE item_code = %s AND uom = %s
        """, (item_code, uom), as_dict=True)
        if item_rate and item_rate[0] and item_rate[0]['price_list_rate']:
            return float(item_rate[0]['price_list_rate'])
        else:
            return False
    except Exception as e:
        return f" Exception Validate Item Description Error: {str(e)} "



def qty_check(json_qty, item_code, warehouse):
    float_json_qty = float(json_qty)
    try:
        bin_query = frappe.db.sql(f""" 
                                  SELECT actual_qty
                                  FROM `tabBin`
                                  WHERE item_code = '{item_code}' AND warehouse = '{warehouse}'
                                    """, as_dict = True)
        if bin_query and bin_query[0]:
            for qty in bin_query:
                data_actual_qty = qty.actual_qty
                if data_actual_qty >= float_json_qty:
                    return float_json_qty
                else:
                    return False
    except Exception as e:
        return f"Exception Bin Proccess Error: {str(e)}"






####################################### Create A Connector 

@frappe.whitelist()
def search_items_to_connector():
    items = frappe.db.sql("""SELECT name , item_name , description , creation FROM tabItem ti """ ,as_dict = True )
    results_list = list()
    for item in items:
        item_dict = {
        "id":  item.name,  
        "title": item.item_name ,  
        "text": item.description,
        "created_at": str(item.creation),  
        } 
        results_list.append(frappe._dict(item_dict))
    # item_category = frappe.db.sql("""""")
    _json = {
        "results" : results_list
    }   
    return _json 

                          
