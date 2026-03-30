'use strict';

(function ($) {
  var content  = $('#head, #body').smoothState({
    debug: true,
    prefetch: true,
    cacheLength: 2,
    
    onStart: {
      duration: 250,
      render: function () {
        content.toggleAnimationClass("is-exiting");
        console.log("inside render function. added 'is-exiting'");
      }
    }
    
  }).data("smoothState");
  console.log("smoothState initialized");
})(jQuery);
