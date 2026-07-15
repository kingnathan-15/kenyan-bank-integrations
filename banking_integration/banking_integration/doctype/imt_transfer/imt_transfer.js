// Copyright (c) 2026, Nathan Wagacha and contributors
// For license information, please see license.txt

frappe.ui.form.on("IMT Transfer", {
    send_transfer(frm) {
        frappe.call({
            method: "banking_integration.api.jenga.send_imt_transfer",
            args: {
                transfer: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Sending IMT Transfer..."),
            callback(r) {
                if (!r.exc) {
                    frappe.show_alert({
                        message: __("IMT Transfer sent successfully"),
                        indicator: "green"
                    });

                    frm.reload_doc();
                }
            }
        });
    },
    recipient_type(frm) {
        const mapping = {
            "Internal Bank": "InternalFundsTransfer",
            "Mobile Wallet": "MobileWallet",
            "Pesalink Account": "Pesalink",
            "Pesalink Mobile": "Pesalink"
        };

        frm.set_value("transfer_type", mapping[frm.doc.recipient_type] || "");
    }
});