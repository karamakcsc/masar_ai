// Copyright (c) 2024, KCSC and contributors
/// For license information, please see license.txt

frappe.ui.form.on("AI Worker", {
	submit: function(frm){
        frappe.call({
            method:"masar_ai.api.generate_response_message",
            args:{
                "user_message":frm.doc.user_message,
            },
            freeze: true,
            freeze_message: 'Please wait...',
            callback: function(r){
                frm.set_value('response', r.message);
            }
        });
    },
    on_submit: function(frm){
        frappe.call({
            method:'masar_ai.api.create_po', 
            args:{
                company : frm.doc.company , 
                supplier : frm.doc.supplier, 
                ai_json : frm.doc.response 
            }, 
            callback : function(r){
                console.log(r.message); 
                
            }
        })
    }
});
