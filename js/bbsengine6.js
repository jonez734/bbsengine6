var bbsengine = (function() {
    let instance = null; // singleton
    let intervals = [];

    return function() {
      if (!instance) {
        instance = {
          logentry: function(message) 
          {
            if (typeof console == "object")
            {
              console.log(message);
            }
            return;
          },

          bedreq: async function(req, justcrc=false) {
            this.logentry("bedreq.100: justcrc="+JSON.stringify(justcrc));

            try {
              return new Promise((resolve, reject) => {
                const csrfToken = this.getCsrfToken();
                let url = ENGINEURL + "bed?req="+encodeURIComponent(req);
                if (justcrc === true) {
                  url += "&justcrc";
                }
                if (csrfToken) {
                  url += "&csrf_token="+encodeURIComponent(csrfToken);
                }
                url += "&callback=?";
                $.ajax({
                  type: "GET",
                  dataType: "jsonp",
                  url: url,
                  error: (xhr, textStatus, errorThrown) => {
                    console.error("bed error: textStatus="+JSON.stringify(textStatus)+" errorThrown="+JSON.stringify(errorThrown));
                    reject(new Error("Bed request failed: " + textStatus));
                  },
                  success: (data) => {
                    this.logentry("=== data="+JSON.stringify(data), "data.status="+JSON.stringify(data.status));
                    resolve(data);
                  },
                }); // ajax
              }); // Promise
            } catch (error) {
              if (error instanceof SyntaxError) {
                console.error("SyntaxError: "+error.message);
              } else {
                console.error("someOtherError: "+error.message);
              }
              throw error; // Re-throw the error for further handling
            }
          },
          // @since 20240915
          getcurrentmoniker: async function() {
            const req = "currentmember.moniker";
            try {
              const data = await this.bedreq(req);
              return data[req];
            } catch(error) {
              console.log("error fetching "+req+":", error.message);
              throw error;
            }
          }, // getcurrentmoniker
          getcurrentid: async function() {
            const req = "currentmember.id";
            try {
              const data = await this.bedreq(req);
              console.log("-- data="+JSON.stringify(data)+" data.currentid="+JSON.stringify(data[req]));
              return data[req];
            } catch(error) {
              console.log("error fetching "+req+":", error.message);
              throw error;
            }

          },
          gettopbarupdateinterval: async function() {
            const req = "config.topbarupdateinterval";
            try {
              const data = await this.bedreq(req);
              return data[req];
            } catch(error) {
              console.log("error fetching "+req+":", error.message);
              throw error;
            }

          },
          getengineurl: async function() {
            const req = "config.getengineurl";
            try {
              const data = await this.bedreq(req);
              return data[req];
            } catch(error) {
              console.log("error fetching "+req+": ", error.message);
              throw error;
            }
          },

          addinterval: function(interval, note, func)
          {
            if (interval === null || interval < 100)
            {
              this.logentry("addinterval.100: "+note+": invalid interval");
              return;
            }
            let id = setInterval(func, interval);
            if (!Array.isArray(this.intervals)) {
              this.intervals = [];
            }
            this.intervals.push([id, interval, func, note]);
            this.logentry("addinterval.110: id="+id+" interval="+interval+" note="+note);
            return;
          },
          cancelintervals: () => {
            this.logentry("canceling intervals");
            this.intervals.forEach(function (item) {
              const id = item[0];
              clearInterval(id);
              instance.logentry("cancelintervals.100: id="+id);
            });
            return;
          },
          restartintervals: () => {
            this.logentry("restarting intervals");
            this.intervals.forEach(function (item, index, arr) {
              const interval = item[1];
              const func = item[2];
              const note = item[3];
              const id = setInterval(func, interval);
              instance.logentry("id="+id+" interval="+interval+" note="+note);
              arr[index][0] = id;
            });
            return;
          },
          updatetopbaritem: async function(req, css="") {
            const selector = $("#topbar "+css);
            if (selector === undefined || selector.length === 0) {
              this.logentry("updatetopbaritem: selector undefined.");
              return;
            }

            const origfragment = selector.clone().wrap("<div>").parent().html();
            if (origfragment === undefined) {
              this.logentry("updatetopbaritem: origfragment is undefined");
              return;
            }
            const origchecksum = this.checksum(origfragment);
            const response = await this.bedreq(req, true);
            if (response === undefined) {
              this.logentry("updatetopbaritem: response to "+JSON.stringify(req)+" is undefined");
              return;
            }

            if (response.checksum === undefined)
            {
              this.logentry("updatetopbaritem: response.checksum undefined");
              return;
            }

            this.logentry("updatetopbaritem: req="+JSON.stringify(req)+" origchecksum="+JSON.stringify(origchecksum)+" new="+JSON.stringify(response.checksum));
            if (origchecksum == response.checksum)
            {
              this.logentry("updatetopbaritem: old and new match");
              return;
            }
            this.logentry("updatetopbaritem: updating "+JSON.stringify(req));
            const csrfToken = this.getCsrfToken();
            let ajaxUrl = ENGINEURL + "bed?req="+encodeURIComponent(req)+"&callback=?";
            if (csrfToken) {
              ajaxUrl += "&csrf_token="+encodeURIComponent(csrfToken);
            }
            $.ajax({
              type: "GET",
              dataType: "jsonp",
              url: ajaxUrl,
              error: (xhr, type, exception) => {
                const err = "textStatus="+JSON.stringify(xhr) + ' type=' + type + " exception="+JSON.stringify(exception);
                this.logentry("updatetopbaritem: req for "+JSON.stringify(req)+" failed: "+JSON.stringify(err));
                return false;
              },
              success: (data) => {
                  selector.fadeOut({
                    duration: 350,
                    complete: () => {
                      const cleanFragment = this.sanitize(data.fragment);
                      selector.replaceWith(cleanFragment);
                      selector.fadeIn(550);
                    }
                  });
              },
            });
          },

        // @since 20240919 generated by chatgpt
        checksum: (str) => {
          let crc = 0xffffffff;
          for (let i = 0; i < str.length; i++) {
            crc ^= str.charCodeAt(i);
            for (let j = 0; j < 8; j++) {
              crc = (crc >>> 1) ^ (-(crc & 1) & 0xedb88320);
            }
          }
          crc ^= 0xffffffff;
          return ('00000000' + (crc >>> 0).toString(16)).slice(-8).toUpperCase();
        },

        sanitize: (dirty) => {
          if (typeof DOMPurify !== 'undefined') {
            return DOMPurify.sanitize(dirty);
          }
          if (typeof console === 'object') {
            console.warn('DOMPurify not loaded - returning raw HTML (XSS risk)');
          }
          return dirty;
        },

        getCsrfToken: () => {
          return window.CSRF_TOKEN || '';
        },

        } // instance of bbsengine
    }; // !instance
    return instance;
  }
})();
