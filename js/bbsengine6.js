// @since 20160221
// singleton inspiration: http://www.dofactory.com/javascript/singleton-design-pattern
var be = null;
var bbsengine = (function () {
    var instance;
//    const self = this;
 
    function createinstance() 
    {
      return {
//        self = this,
        // @since 20160219
        intervals: [],
        visibilityhandler: false,
        // @since 20181021
        currentmemberid: null,
        // @since 20191026
        topbarupdateinterval: 30000,
        // @since 20140210
        logentry: function(message) 
        {
          if (typeof console == "object")
          {
            console.log(message);
          }
          return;
        },
        // @since 20140822
        endswith: function (str, suffix)
        {
          return str.indexOf(suffix, str.length - suffix.length) !== -1;
        },
        appendurlparameter: function (url, param)
        {
          // http://stackoverflow.com/questions/8737615/append-a-param-onto-the-current-url
          var seperator = (url.indexOf("?")===-1)?"?":"&",
              newParam = seperator + param,
              newUrl = url.replace(newParam,"") + newParam;
          return newUrl;
        },
        // http://stackoverflow.com/questions/736513/how-do-i-parse-a-url-into-hostname-and-path-in-javascript
        // @since 20150915
        getlocation: function(href)
        {
          var l = document.createElement("a");
          l.href = href;
          return l;
        },

        initvisibilityeventhandler: function()
        {
          // @see https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API
          var hidden, visibilityChange; 
          if (typeof document.hidden !== "undefined") { // Opera 12.10 and Firefox 18 and later support 
            hidden = "hidden";
            visibilityChange = "visibilitychange";
          } else if (typeof document.mozHidden !== "undefined") {
            hidden = "mozHidden";
            visibilityChange = "mozvisibilitychange";
          } else if (typeof document.msHidden !== "undefined") {
            hidden = "msHidden";
            visibilityChange = "msvisibilitychange";
          } else if (typeof document.webkitHidden !== "undefined") {
            hidden = "webkitHidden";
            visibilityChange = "webkitvisibilitychange";
          }
          // If the page is hidden, stop the intervals
          // if the page is shown, restart the intervals
          function handleVisibilityChange() 
          {
//            instance.logentry("handlevisibilitychange.100: called");
            if (document[hidden])
            {
              be.cancelintervals();
            } 
            else 
            {
              be.restartintervals();
            }
          }

          if (typeof document.addEventListener === "undefined" || typeof hidden === "undefined") 
          {
            instance.logentry("This site requires a browser, such as Google Chrome or Firefox, that supports the Page Visibility API.");
          } 
          else 
          {
            // Handle page visibility change   
            document.addEventListener(visibilityChange, handleVisibilityChange, false);
          }
        },
        
        addinterval: function(interval, note, func)
        {
          if (interval === null || interval < 100)
          {
            instance.logentry("addinterval.100: "+note+": invalid interval");
            return;
          }
          let id = setInterval(func, interval);
          this.intervals.push([id, interval, func, note]);
          instance.logentry("addinterval.110: id="+id+" interval="+interval+" note="+note);
          if (this.visibilityhandler === false)
          {
//            instance.logentry("init visibility event handler");
            this.initvisibilityeventhandler();
            this.visibilityhandler = true;
          }
          return;
        },
        cancelintervals: function() {
          instance.logentry("canceling intervals");
          this.intervals.forEach(function (item/*, index, arr*/) {
            let id = item[0]; // arr[index][0];
            clearInterval(id);
            instance.logentry("cancelintervals.100: id="+id);
          });
          return;
        },
        restartintervals: function() {
          const logentry = instance.logentry;
          logentry("restarting intervals");
          this.intervals.forEach(function (item, index, arr) {
            // const oldid = item[0];
            const interval = item[1];
            const func = item[2];
            const note = item[3];
            const id = setInterval(func, interval);
            logentry("id="+id+" interval="+interval+" note="+note);
            arr[index][0] = id;
          });
          return;
        },
        settopbarupdateinterval: function(interval) {
          this.topbarupdateinterval = interval;
        },
//        gettopbarupdateinterval: function() {
//          return this.topbarupdateinterval || 5000;
//        },
        // from http://mediocredeveloper.com/wp/?p=55
        hashcode: function(str) {
          // instance.logentry("hashcode.100: s="+JSON.stringify(typeof s));
          if (typeof str  !== "string")
          {
            instance.logentry("hashcode passed a non-string");
            return -1;
          }
          var hash = 0;
          if (str.length === 0) return hash;
          for (let i = 0; i < str.length; i++) {
            let ch = str.charCodeAt(i);
            hash = ((hash << 5)-hash) + ch;
            hash = hash & hash; // Convert to 32bit integer
          }
          // it would be nice if this could be unsigned
          hash = Math.abs(hash);
          hash = hash.toString(16);
          return hash;
        },
        // @since 20180916
        updatetopbaritem: function(label, selector, url) {
          // be.logentry("updatetopbaritem.100: running");
          if (selector === undefined || selector.length === 0) {
            // be.logentry("updatetopbaritem: "+label+" selector is undefined");
            return;
          }
          // be.logentry("updatetopbaritem: url="+url);

          $.ajax({
            type: "GET",
            dataType: "jsonp",
            url: url,
            error: function(xhr, type, exception) {
              var err = "textStatus="+JSON.stringify(xhr) + ' type=' + type + " exception="+JSON.stringify(exception);
              be.logentry("updatetopbaritem.error: "+ err);
            }, /* end 'error' */
            success: function(payload) {
              var oldfragment = selector;
              var fragment = null;

              var a = selector.clone();
              var b = a.wrap("<div>");
              var c = b.parent();
              var d = c.html();
              oldfragment = d;
              // be.logentry("label: " + label);
              if (oldfragment === undefined)
              {
                instance.logentry("updatetopbaritem.success.100: oldfragment is undefined");
                return;
              }
              fragment = payload.fragment.trim();

              if (fragment != oldfragment) {
                be.logentry("fragment="+JSON.stringify(fragment));
                instance.logentry("oldfragment="+JSON.stringify(oldfragment));
                instance.logentry("updatetopbar.success.100: fragment != oldfragment. updating");
                selector.fadeOut({
                  duration: 350,
                  complete: function(/* data */) {
                    // be.logentry("updatetopbar.fadeout.complete: oldfragment="+JSON.stringify(oldfragment));
                    
                    selector.replaceWith(fragment);
                    selector.fadeIn(500);
                    
                    oldfragment = fragment;
                  }
                });
              } /* oldfragment != fragment */
            } /* end 'success' */
          }); /* .ajax */
        }, /* updatetopbaritem */
        getcurrentmemberid: function () {
          return new Promise((resolve, reject) => {
            $.ajax({
              type: "GET",
              dataType: "jsonp",
              url: "//engine.zoidtechnologies.com/getvar-currentmemberid?callback=?",
              error: function(error) {
                reject(error)
              },
              success: function(data) {
                resolve(data.currentmemberid);
              },
            }); /* .ajax */
          });
        },
        gettopbarupdateinterval: function () {
          return new Promise(function (resolve, reject) {
            $.ajax({
              type: "GET",
              dataType: "jsonp",
              url: "//engine.zoidtechnologies.com/getvar-topbarupdateinterval?callback=?",
              error: function(error) {
                reject(error);
              }, /* error */
              success: function(data) {
                console.log("gettopbarupdateinterval.100: success: data="+JSON.stringify(data.topbarupdateinterval));
                resolve(data.topbarupdateinterval);
              }, /* success */
            }); /* .ajax */
          }); /* new Promise */
        }, /* gettopbarupdateinterval */
      }
    }
    return {
      getinstance: function () {
        if (!instance) {
          instance = createinstance();
//          instance.getcurrentmemberid().done(function (r) { instance.currentmemberid = r.currentmemberid; });
          instance.getcurrentmemberid().then(data => {
            instance.currentmemberid = data;
            console.log("currentmemberid="+data);
          })
          .catch(error => {
              console.log(error);
          });

/*
          instance.logentry("before await");
          instance.topbarupdateinterval = await instance.gettopbarupdateinterval();
          console.log("instance.topbarinterval (await).100: interval="+be.topbarupdateinterval);
*/
          instance.gettopbarupdateinterval().then(data => {
            instance.topbarupdateinterval = data;
            console.log("updateinterval="+data);
          })
          .catch(error => {
            console.log(error);
          });
        } /* !instance */

        instance.logentry("instance.topbarupdateinterval="+JSON.stringify(instance.topbarupdateinterval));
        return instance;
      },
    };
})();

function getbbsengine() {
//  console.log("getbbsengine called");
  var be = bbsengine.getinstance();
  console.log("getbbsengine.100: be="+JSON.stringify(be));
  return be; // bbsengine.getinstance();
}
