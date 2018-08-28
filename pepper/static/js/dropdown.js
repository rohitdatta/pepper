$(document).ready(function(){
    $('select').on('change', function(){ 
        if ($(this).val() !== ""){ 
            $(this).addClass('selected-option'); 
        } else {
             $(this).removeClass('selected-option');
        }
    });
});