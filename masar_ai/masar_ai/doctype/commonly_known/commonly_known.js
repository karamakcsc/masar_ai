// Copyright (c) 2024, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commonly Known", {
    submit: function(frm) {
        frappe.call({
            method: "masar_ai.api.generate_commonly_known",
            args: {
                "dynamic_doc": frm.doc.document,
            },
            freeze: true,
            freeze_message: 'Please wait...',
            callback: function(r) {
                frm.set_value('commonly_known', r.message);
            }
        });
    },
});