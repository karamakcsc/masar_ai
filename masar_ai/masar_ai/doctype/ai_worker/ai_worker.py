# Copyright (c) 2024, KCSC and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
import requests
import json
from frappe.model.document import Document
from masar_ai.api import (base_request_data , 
						validate_json_text , 
						proccess_search_items , 
						validate_item_description , 
						search_in_commonly_known_names ,
                        qty_check , get_supplier , cohere_api_key_and_url)

class AIWorker(Document):
	def validate(self):
		self.availablity_item_and_qty()

	def availablity_item_and_qty(self):
		data_ai = validate_json_text(self.response)
		# base_url, headers = base_request_data()
		self.available_items_and_qty.clear()
		self.unavailable_qty.clear()
		self.unavailable_item.clear()
		items = data_ai['order']['items']
		get_supplier_json = data_ai['order']['supplier']
		supplier_json = get_supplier( supplier_json= get_supplier_json)
		item_code_po = None 
		if supplier_json:
			supplier_po = supplier_json
		else: 
			supplier_po = self.supplier
		warehouse = "Stores - KCSCD"
		if not supplier_po:
			frappe.throw("Supplier Not Exist in Supplier Field OR In JSON File.")
		for item in items:
			item_code = proccess_search_items(item["item"] , item["item"])
			if item_code:
				item_code_po = item_code
			else :
				item_code_from_description =  validate_item_description(item["item"])
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
					if item_code_po: 
						qty = qty_check(item["qty"], item_code_po, warehouse)
				if item_code_po:
					item_name = frappe.db.sql("""SELECT item_name FROM 	`tabItem` WHERE name = %s""",(item_code_po) , as_dict = True ) [0]['item_name']
					actual_qty = frappe.db.sql(f"""SELECT actual_qty FROM `tabBin` WHERE item_code = '{item_code_po}'""")
					unavailable_qty =item["qty"]
					if qty:
						if qty <= actual_qty:
							qty_child = qty
						if qty >= actual_qty:
							unavailable_qty = item["qty"]
				
				
				if item_code_po and qty:
					self.append('available_items_and_qty', {
						"item_code": item_code_po,
						"item_name": item_name,
						"qty": qty_child,
					})
				elif item_code_po and not qty:
					self.append('unavailable_qty', {
						"item_code": item_code_po,
						"item_name": item_name,
						"request_qty": unavailable_qty,
						"available_qty": actual_qty[0][0] if actual_qty else 0,
					})
				elif not item_code_po:
					self.append('unavailable_item', {
						"item": item["item"],
					})
		
		return "True"
