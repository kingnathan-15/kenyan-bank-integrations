// Copyright (c) 2026, Nathan Wagacha and contributors
// For license information, please see license.txt

const TRANSFER_TYPES_BY_BANK = {
    "Equity Bank Kenya": [
        "Internal Bank Transfer",
        "EFT",
        "RTGS",
        "Pesalink Bank",
        "Pesalink Mobile",
        "SWIFT",
        "Mobile Wallet",
    ],

    "Stanbic Bank Kenya": [
        "EFT",
        "Pesalink Bank",
        "Pesalink Mobile",
        "RTGS",
        "Mobile Wallet",
        "B2C",
        "STK Push",
        "Internal Bank Transfer",
    ],

    "KCB Bank Kenya": [
        "EFT",
        "RTGS",
        "Pesalink Bank",
        "Pesalink Mobile",
        "Mobile Wallet",
        "Internal Bank Transfer",
    ],
};


frappe.ui.form.on("Bank Transfer", {

    refresh(frm) {
        const is_new = frm.is_new();

        // Bank Transfer is a tracking document.
        // Users should not create one directly.
        if (is_new) {
            frm.disable_save();
        }

        // Only allow sending an existing transfer.
        if (
            !is_new &&
            ["Draft", "Pending Approval"].includes(frm.doc.status)
        ) {
            frm.add_custom_button(
                __("Send Transfer"),
                () => {
                    confirm_and_send_transfer(frm);
                }
            );
        }

        set_transfer_type_options(frm);
    },

    bank(frm) {
        set_transfer_type_options(frm);
    },
});


function set_transfer_type_options(frm) {
    const options =
        TRANSFER_TYPES_BY_BANK[frm.doc.bank] || [];

    frm.set_df_property(
        "transfer_type",
        "options",
        options.join("\n")
    );

    if (
        frm.doc.transfer_type &&
        !options.includes(frm.doc.transfer_type)
    ) {
        frm.set_value(
            "transfer_type",
            ""
        );
    }
}


function confirm_and_send_transfer(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Confirm Your Identity"),

        fields: [
            {
                fieldname: "password",
                fieldtype: "Password",
                label: __(
                    "Enter your ERPNext password to authorize this transfer"
                ),
                reqd: 1,
            },
        ],

        primary_action_label: __(
            "Send Transfer"
        ),

        primary_action(values) {
            dialog.hide();

            frappe.call({
                method:
                    "banking_integration.banking_integration.doctype.bank_transfer.bank_transfer.approve_and_send",

                args: {
                    bank_transfer:
                        frm.doc.name,

                    password:
                        values.password,
                },

                freeze: true,

                freeze_message: __(
                    "Sending transfer..."
                ),

                callback(r) {
                    if (!r.exc) {
                        frm.reload_doc();
                    }
                },
            });
        },
    });

    dialog.show();
}