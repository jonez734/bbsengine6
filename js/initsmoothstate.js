/**
 * initsmoothstate.js - Initialize smoothState page transitions
 * @description Handles progressive page loading
 */
'use strict';

(function($) {
  var content = $('#head, #body').smoothState({
    debug: false,
    prefetch: true,
    cacheLength: 2,

    onStart: {
      duration: 250,
      render: function() {
        content.toggleAnimationClass("is-exiting");
      }
    }

  }).data("smoothState");
})(jQuery);