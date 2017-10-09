$(function () {
    $(".unverified-user").click(function () {
        //TODO Get the button clicked
        email = this.id;
        console.log(email);
        $.ajax({
            url: '/admin/resend-corp-invite',
            method: 'POST',
            beforeSend: function () {
                $("#refresh").prop("disabled", true);
            },
            success: function (data) {
                toastr.success('Successfully resent email confirmation');
                $("#refresh").prop("disabled", false);
            },
            error: function () {
                toastr.error('Unable to resend email confirmation');
                $("#refresh").prop("disabled", false);
            }
        });
    });
});