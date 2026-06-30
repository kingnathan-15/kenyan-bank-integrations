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

    },

    get_statement(frm) {
        frappe.call({
            method: "banking_integration.services.accounts.sync_statement",
            args: {
                account: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Fetching account statement...")
        }).then((r) => {
            if (r.message && r.message.status === "success") {
                // Build a clean, informative message showing both counts
                let msg = __("Sync complete! {0} new transactions imported.", [r.message.imported]);
                if (r.message.already_exists > 0) {
                    msg += "<br><small class='text-muted'>" + __("{0} existing transactions skipped.", [r.message.already_exists]) + "</small>";
                }
                
                frappe.msgprint({
                    title: __('Jenga Sync Summary'),
                    message: msg,
                    indicator: 'green'
                });

                // Reloads the doc so your 'recent_statements' child table updates instantly
                frm.reload_doc();
            }
        });
    }
});
// 	},
// });
