// Submit on change of Rating/Comment
$(".form-check").change(function(){
  $("form").submit();
})

$("textarea").change(function(){
  $("form").submit();
})
