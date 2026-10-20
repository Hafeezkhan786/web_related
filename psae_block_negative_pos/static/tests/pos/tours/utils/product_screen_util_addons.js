export function isErrorDialogShown(val="") {
    return [
        {
            timeout: 5000,
            content: `input shown is '${val}'`,
            trigger: `.modal .modal-header:contains("${val}")`,
        },
    ];
}
