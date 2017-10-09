$(function () {
    // ask for confirmation before doing anything funky with teams
    $('form').submit(function (e) {
        if (this.id == 'remove') {
            if (window.confirm('Are you sure you want to remove this user from your team?')) {
                return true;
            }
            e.preventDefault();
            return false;
        } else {
            if (window.confirm('Are you sure you want to ' + this.id + ' your team?')) {
                return true;
            }
            e.preventDefault();
            return false;
        }

    });
});
