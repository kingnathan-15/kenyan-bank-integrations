frappe.ui.form.on("Bank Account", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Refresh Balance"), () => {
                frappe.call({
                    method: "banking_integration.services.bank_account.refresh_balance",
                    args: {
                        bank_account: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __("Fetching balance from bank..."),
                    callback(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: __("Balance updated successfully"),
                                indicator: "green"
                            });
                        }
                    }
                });
            });
        }
    }
});