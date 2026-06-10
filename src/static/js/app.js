document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("[data-live-filter]");
    if (!form) {
        return;
    }

    const search = form.querySelector('input[name="q"]');
    const selects = form.querySelectorAll("select");
    let timer;

    const submit = () => form.requestSubmit();
    search.addEventListener("input", () => {
        window.clearTimeout(timer);
        timer = window.setTimeout(submit, 350);
    });
    selects.forEach((select) => select.addEventListener("change", submit));
});

