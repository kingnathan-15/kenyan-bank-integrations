// Copyright (c) 2026, Nathan Wagacha and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accounts", {

    refresh_balance(frm) {

        frappe.call({
            method:
                "banking_integration.api.jenga.get_account_balance",

            args: {
                account: frm.doc.name
            },

            callback(r) {

                frm.reload_doc();

                frappe.show_alert("Balance updated");
            }
        });

    },

    refresh(frm) {

        if (!frm.is_new()) {

            frm.add_custom_button(
                "Refresh Balance",
                () => frm.trigger("refresh_balance")
            );

        }

    }

});

// 	},
// });
