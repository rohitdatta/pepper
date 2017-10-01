const toastr = window.toastr;

toastr.options = {positionClass: 'toast-top-center'}

/* turning flask flash messages into js popup notifications */
window.popupMessages.forEach(function (m, i) {
    var category = m[0] || 'info';
    var text = m[1];
    setTimeout(function () {
        toastr[category](text)
    }, (1 + i) * 1500)
});
