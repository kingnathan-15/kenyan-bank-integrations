// Copyright (c) 2026, Nathan Wagacha and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Transfer", {
    send_transfer(frm) {
        frappe.call({
            method: "banking_integration.api.jenga.send_transfer",
            args: {
                transfer: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Sending transfer..."),
            callback(r) {
                if (!r.exc) {
                    frm.reload_doc();
                }
            }
        });
    }
});