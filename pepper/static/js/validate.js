// Wait for the DOM to be ready
$(function() {

    function toggleGenderColumns() {
        if ($('#dropdown-gender').val() === 'Other') {
            $('#input-gender-container').show();
            $('#dropdown-gender-container').removeClass('col-md-12').addClass('col-md-6');
        } else {
            $('#input-gender-container').hide();
            $('#dropdown-gender-container').removeClass('col-md-6').addClass('col-md-12');
        }
    }

    toggleGenderColumns();

    $("#dropdown-gender").change(toggleGenderColumns);

    jQuery.validator.addMethod("facebook", function(value, element) {
        return this.optional(element) || /[a-zA-Z0-9\.]+/.test(value);
    }, "Please enter a valid Facebook username");

    // Initialize form validation on the registration form.
    // It has the name attribute "registration"
    $("#edit-information").validate({
        ignore:":not(:visible)",
        // Specify validation rules
        rules: {
            // The key name on the left side is the name attribute
            // of an input field. Validation rules are defined
            // on the right side
            first_name: "required",
            last_name: "required",
            email: {
                required: true,
                // Specify that email should be validated
                // by the built-in "email" rule
                email: true
            },
            phone_number: "required",
            date_of_birth: "required",
            gender: "required",
            gender_other: "required",
            shirt_size: "required",
            school_name: "required",
            major: "required",
            dietary_restrictions: "required",
            skill_level: "required",
            num_hackathons: {
                required: true,
                min: 0,
                max: 9223372036854775807,
                digits: true
            },
            class_standing: "required",
            race: "required",
            facebook_account: {
                required: ".campus-ambassador-checkbox:checked",
                facebook: true
            },
            campus_ambassadors_application: {
                required: ".campus-ambassador-checkbox:checked"
            },
            mlh: "required"
        },
        // Specify validation error messages
        messages: {
            fname: "Please enter your first name",
            lname: "Please enter your last name",
            email: "Please enter a valid email address",
            phone_number: "Please enter your phone number",
            password: {
                required: "Please provide a password",
                minlength: "Your password must be at least 8 characters long"
            },
            date_of_birth: "Please enter your birth date",
            gender: "Please identify your gender identity",
            gender_other: "Please identify your gender identity",
            shirt_size: "Please choose your shirt size",
            school_name: "Please enter your school name",
            major: "Please enter your major",
            dietary_restrictions: "Please choose your dietary restriction",
            skill_level: "Please enter your skill level",
            num_hackathons: "Please enter the number of hackathons you've been to. It's ok to say 0!",
            class_standing: "Please choose your class standing",
            race: "Please select your race",
            facebook_account: "Please enter your Facebook username",
            campus_ambassadors_application: "Please enter your campus ambassador application",
            mlh: "Please agree to the MLH Code of Conduct"
        },
        errorPlacement: function(error, element) {
            if (element.hasClass("form-control")) {
                element.parent(".input-group").after(error);
            } else {
                element.after(error);
            }
        }
        // Make sure the form is submitted to the destination defined
        // in the "action" attribute of the form when valid
    });

    $("#edit_local").validate({
        ignore:":not(:visible)",
        // Specify validation rules
        rules: {
            // The key name on the left side is the name attribute
            // of an input field. Validation rules are defined
            // on the right side
            fname: "required",
            lname: "required",
            email: {
                required: true,
                // Specify that email should be validated
                // by the built-in "email" rule
                email: true
            },
            phone_number: "required",
            old_password: {
                required: true
            },
            date_of_birth: "required",
            gender: "required",
            gender_other: "required",
            shirt_size: "required",
            school_name: "required",
            major: "required",
            dietary_restrictions: "required"
        },
        // Specify validation error messages
        messages: {
            fname: "Please enter your first name",
            lname: "Please enter your last name",
            email: "Please enter a valid email address",
            phone_number: "Please enter your phone number",
            old_password: {
                required: "Please enter your original password"
            },
            date_of_birth: "Please enter your birth date",
            gender: "Please identify your gender identity",
            gender_other: "Please identify your gender identity",
            shirt_size: "Please choose your shirt size",
            school_name: "Please enter your school name",
            major: "Please enter your major",
            dietary_restrictions: "Please choose your dietary restriction"
        },
        // Make sure the form is submitted to the destination defined
        // in the "action" attribute of the form when valid
    });
});
