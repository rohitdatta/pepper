// Wait for the DOM to be ready
$(function() {
	$("#dropdown_gender").change(function() {
		var selected = $(this).val();
		$('#input_gender').css('display', (selected === 'Other') ? 'block' : 'none');
	});

	// Initialize form validation on the registration form.
  	// It has the name attribute "registration"
  	$("#register_local").validate({
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
    	password: {
    		required: true,
    		minlength: 8
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
    	dietary_restrictions: "Please choose your dietary restriction"   	
    },
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