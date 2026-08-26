frappe.listview_settings["Account Statement"] = {
    onload(listview) {
        listview.page.add_inner_button(
            __("Bulk Reconcile"),
            () => {
                show_bulk_reconciliation_dialog(listview);
            }
        );
    },
};


function show_bulk_reconciliation_dialog(listview) {
    const dialog = new frappe.ui.Dialog({
        title: __("Bulk Reconciliation"),

        fields: [
            {
                fieldname: "bank",
                fieldtype: "Select",
                label: __("Bank"),
                options: [
                    "Jenga",
                    "Stanbic",
                    "All Banks",
                ],
                default: "Jenga",
                reqd: 1,
            },
        ],

        primary_action_label: __("Reconcile"),

        primary_action(values) {
            dialog.hide();

            let method;

            if (values.bank === "Jenga") {
                method =
                    "banking_integration.api.jenga.bulk_reconcile_statements";
            }

            else if (values.bank === "Stanbic") {
                method =
                    "banking_integration.api.stanbic.bulk_reconcile_account_statements";
            }

            else {
                method =
                    "banking_integration.api.jenga.bulk_reconcile_statements";
            }

            frappe.call({
                method: method,

                args: {
                    bank: values.bank,
                },

                freeze: true,

                freeze_message: __(
                    "Reconciling Account Statements..."
                ),

                callback(r) {
                    if (!r.message) {
                        return;
                    }

                    const result = r.message;

                    frappe.msgprint({
                        title: __("Bulk Reconciliation Complete"),

                        indicator:
                            result.errors > 0
                                ? "orange"
                                : "green",

                        message: `
                            <p>
                                <strong>Bank:</strong>
                                ${values.bank}
                            </p>

                            <p>
                                <strong>Total:</strong>
                                ${result.total ??
                                    result.processed ??
                                    0}
                            </p>

                            <p>
                                <strong>Matched:</strong>
                                ${result.matched ?? 0}
                            </p>

                            <p>
                                <strong>Unmatched:</strong>
                                ${result.unmatched ?? 0}
                            </p>

                            <p>
                                <strong>Multiple Matches:</strong>
                                ${result.multiple_matches ?? 0}
                            </p>

                            <p>
                                <strong>Already Reconciled:</strong>
                                ${result.already_matched ?? 0}
                            </p>

                            ${
                                result.errors
                                    ? `
                                        <p>
                                            <strong>Errors:</strong>
                                            ${result.errors}
                                        </p>
                                    `
                                    : ""
                            }
                        `,
                    });

                    listview.refresh();
                },
            });
        },
    });

    dialog.show();
}