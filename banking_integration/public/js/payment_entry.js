frappe.ui.form.on("Payment Entry", {
    before_submit(frm) {
        return new Promise((resolve, reject) => {

            const dialog = new frappe.ui.Dialog({
                title: __("Bank Transfer Type"),
                fields: [
                    {
                        fieldname: "transfer_type",
                        label: __("Transaction Type"),
                        fieldtype: "Select",
                        options: [
                            "EFT",
                            "RTGS",
                            "Pesalink Bank",
                            "Pesalink Mobile",
                            "SWIFT",
                            "Mobile Wallet",
                            "Internal Bank Transfer"
                        ],
                        reqd: 1
                    }
                ],

                primary_action_label: __("Continue"),

                primary_action(values) {

                    if (!values.transfer_type) {
                        frappe.msgprint(
                            __("Please select a transaction type.")
                        );
                        return;
                    }

                    // Store the selection on the Payment Entry
                    frm.set_value(
                        "custom_bank_transfer_type",
                        values.transfer_type
                    );

                    dialog.hide();

                    resolve();
                }
            });

            dialog.show();

            // If the user closes the dialog without selecting
            dialog.$wrapper.on("hidden.bs.modal", function () {

                if (!frm.doc.custom_bank_transfer_type) {
                    reject();
                }

            });
        });
    }
});