frappe.ui.form.on("Account Statement", {
    refresh(frm) {
        frm.add_custom_button(
            __("Get Statement"),
            () => show_statement_dialog(frm)
        );

        if (!frm.is_new()) {
            frm.add_custom_button(
                __("Reconcile"),
                () => reconcile_statement(frm)
            );
        }
    },
});


function reconcile_statement(frm) {
    frappe.call({
        method:
            "banking_integration.api.jenga.reconcile_account_statement",

        args: {
            statement: frm.doc.name,
        },

        freeze: true,
        freeze_message: __("Reconciling statement..."),

        callback(response) {
            const result = response.message;

            if (!result) return;

            if (result.status === "matched") {
                frappe.msgprint({
                    title: __("Reconciliation Successful"),
                    indicator: "green",
                    message: `
                        <p><strong>Status:</strong> Matched</p>
                        <p><strong>Document Type:</strong>
                        ${result.matched_document_type}</p>
                        <p><strong>Document:</strong>
                        ${result.matched_document}</p>
                    `,
                });
            }

            else if (result.status === "already_matched") {
                frappe.msgprint({
                    title: __("Already Reconciled"),
                    indicator: "blue",
                    message: __("This statement has already been reconciled."),
                });
            }

            else if (result.status === "multiple_matches") {
                const matches = result.matches
                    .map(
                        match =>
                            `<li>${match.doctype}: ${match.name}</li>`
                    )
                    .join("");

                frappe.msgprint({
                    title: __("Multiple Matches Found"),
                    indicator: "orange",
                    message: `
                        <p>
                            More than one ERPNext transaction
                            matches this statement.
                        </p>
                        <ul>${matches}</ul>
                        <p>Please reconcile this transaction manually.</p>
                    `,
                });
            }

            else if (result.status === "unmatched") {
                frappe.msgprint({
                    title: __("No Match Found"),
                    indicator: "orange",
                    message: __("No matching ERPNext transaction was found."),
                });
            }

            frm.reload_doc();
        },
    });
}


function show_statement_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Get Bank Statement"),

        fields: [
            {
                fieldname: "account",
                fieldtype: "Link",
                label: __("Bank Account"),
                options: "Bank Account",
                reqd: 1,
                default: frm.doc.account,
            },
            {
                fieldname: "from_date",
                fieldtype: "Date",
                label: __("From Date"),
                reqd: 1,
                default: frappe.datetime.month_start(),
            },
            {
                fieldname: "to_date",
                fieldtype: "Date",
                label: __("To Date"),
                reqd: 1,
                default: frappe.datetime.get_today(),
            },
        ],

        primary_action_label: __("Import"),

        primary_action(values) {
            if (values.from_date > values.to_date) {
                frappe.msgprint({
                    title: __("Invalid Date Range"),
                    message: __("From Date cannot be later than To Date."),
                    indicator: "red",
                });
                return;
            }

            dialog.hide();

            frappe.db.get_value(
                "Bank Account",
                values.account,
                "bank"
            ).then(response => {
                const bank = response.message?.bank;

                if (!bank) {
                    frappe.msgprint({
                        title: __("Bank Not Set"),
                        message: __(
                            "The selected Bank Account does not have a Bank specified."
                        ),
                        indicator: "red",
                    });
                    return;
                }

                const is_stanbic =
                    bank.toLowerCase().includes("stanbic");

                if (is_stanbic) {
                    import_stanbic(
                        values,
                        bank
                    );
                } else {
                    import_jenga(
                        values,
                        bank
                    );
                }
            });
        },
    });

    dialog.show();
}


function import_stanbic(values, bank) {
    frappe.call({
        method:
            "banking_integration.api.stanbic.fetch_statements",

        args: {
            account: values.account,
            from_date: values.from_date,
            to_date: values.to_date,
        },

        freeze: true,
        freeze_message: __("Importing Stanbic statement..."),

        callback(response) {
            show_import_result(
                response.message,
                bank
            );
        },
    });
}


function import_jenga(values, bank) {
    frappe.call({
        method:
            "banking_integration.api.jenga.import_jenga_statement",

        args: {
            account: values.account,
            from_date: values.from_date,
            to_date: values.to_date,
        },

        freeze: true,
        freeze_message: __("Importing Jenga statement..."),

        callback(response) {
            show_import_result(
                response.message,
                bank
            );
        },
    });
}


function show_import_result(result, bank) {
    if (!result) return;

    frappe.msgprint({
        title: __("Statement Import Complete"),
        indicator: "green",

        message: `
            <p>
                <strong>Bank:</strong>
                ${bank}
            </p>

            <p>
                <strong>Account:</strong>
                ${result.account || ""}
            </p>

            <p>
                <strong>Transactions:</strong>
                ${result.transactions || 0}
            </p>

            <p>
                <strong>Created:</strong>
                ${result.created || 0}
            </p>

            <p>
                <strong>Skipped:</strong>
                ${result.skipped || 0}
            </p>

            ${
                result.balance !== undefined
                    ? `
                        <p>
                            <strong>Balance:</strong>
                            ${result.balance}
                            ${result.currency || ""}
                        </p>
                    `
                    : ""
            }
        `,
    });

    cur_frm.reload_doc();
}