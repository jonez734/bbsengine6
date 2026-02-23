// Contents of functions.js

// @see https://css-tricks.com/add-page-transitions-css-smoothstate-js/
(function ($) {
  'use strict';
  var content  = $('#head, #body').smoothState({
    debug: true,
    prefetch: true,
    cacheLength: 2,
    
    // onStart runs as soon as link has been activated
    onStart: {
          
      // Set the duration of our animation
      duration: 250,
          
      // Alterations to the page
      render: function () {
        // Quickly toggles a class and restarts css animations
        content.toggleAnimationClass("is-exiting");
        // smoothState.restartCSSAnimations(); // toggleanimationclass('is-exiting');
        console.log("inside render function. added 'is-exiting'");
      }
    }
    
  /*
    onReady: {
      duration: 1000,
      render: function($container, $newContent) {
        $container.removeClass('is-exiting');
        $container.html($newContent);
        console.log("smoothState onReady fired");
      }
    }
  */
  }).data("smoothState");
//      smoothState = $('#main').smoothState(options).data('smoothState');
      // }).data('smoothState'); // makes public methods available
  console.log("smoothState initialized");
})(jQuery);

/*
;(function($) {
  'use strict';
  var $body = $('html, body'),
      content = $('#smoothstatecontainer').smoothState({
        // Runs when a link has been activated
        onStart: {
          duration: 250, // Duration of our animation
          render: function (url, $container) {
            // toggleAnimationClass() is a public method
            // for restarting css animations with a class
            content.toggleAnimationClass('is-exiting');
            // Scroll user to the top
            $body.animate({
              scrollTop: 0
            });
          }
        }
      }).data('smoothState');
      //.data('smoothState') makes public methods available
})(jQuery);
*/
/*
$(function(){
  'use strict';
  console.log("running smoothstate init");
  var $page = $('#main'), // html, body
      options = {
        debug: true,
        prefetch: true,
        allowFormCaching: false,
        repeatDelay: 750,
        cacheLength: 2,
        blacklist:  'form',
        forms: 'form',
        onStart: {
          duration: 2000, // Duration of our animation
          render: function ($container) {
            console.log("called render onStart");
            // Add your CSS animation reversing class
            $container.addClass('is-exiting');
            // Restart your animation
            smoothState.restartCSSAnimations();
          }
        },
        onReady: {
          duration: 0,
          render: function ($container, $newContent) {
            console.log("called render onReady");
            // Remove your CSS animation reversing class
            $container.removeClass('is-exiting');
            // Inject the new content
            $container.html($newContent);
          }
        }
      },
      smoothState = $page.smoothState(options).data('smoothState');
});
*/
