$(document).ready(function () {
    $("#accept").click(function () {
        $("#accept").toggleClass("selected");
        $("#reject").removeClass("selected");
        $("#reject-area").hide();
        $("#accept-fields").toggle();
    });
    $("#reject").click(function () {
        $("#reject").toggleClass("selected");
        $("#accept").removeClass("selected");
        $("#accept-fields").hide();
        $("#reject-area").toggle();
    });
});