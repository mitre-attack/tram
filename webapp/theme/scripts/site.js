$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})

 // function to set the height on fly
 function autoHeight() {
 	console.log($('#header').height() );
   $('#content').css('min-height', 0);
   $('#content').css('min-height', (
     $(document).height() 
     - 250
   ));
 }

 // onDocumentReady function bind
 $(document).ready(function() {
   autoHeight();
 });

 // onResize bind of the function
 $(window).resize(function() {
   autoHeight();
 });

 $('.carousel').carousel()