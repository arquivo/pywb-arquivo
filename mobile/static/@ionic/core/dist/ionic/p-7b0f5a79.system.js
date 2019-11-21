System.register(["./p-78563a64.system.js"],function(e){"use strict";var t;return{setters:[function(e){t=e.p}],execute:function(){e("startInputShims",S);var n=new WeakMap;function r(e,t,r,a){if(a===void 0){a=0}if(n.has(e)===r){return}if(r){o(e,t,a)}else{i(e,t)}}function a(e){return e===e.getRootNode().activeElement}function o(e,t,r){var a=t.parentNode;var o=t.cloneNode(false);o.classList.add("cloned-input");o.tabIndex=-1;a.appendChild(o);n.set(e,o);var i=e.ownerDocument;var u=i.dir==="rtl"?9999:-9999;e.style.pointerEvents="none";t.style.transform="translate3d("+u+"px,"+r+"px,0) scale(0)"}function i(e,t){var r=n.get(e);if(r){n.delete(e);r.remove()}e.style.pointerEvents="";t.style.transform=""}function u(e,t,n){if(!n||!t){return function(){return}}var o=function(n){if(a(t)){r(e,t,n)}};var i=function(){return r(e,t,false)};var u=function(){return o(true)};var s=function(){return o(false)};n.addEventListener("ionScrollStart",u);n.addEventListener("ionScrollEnd",s);t.addEventListener("blur",i);return function(){n.removeEventListener("ionScrollStart",u);n.removeEventListener("ionScrollEnd",s);t.addEventListener("ionBlur",i)}}var s="input, textarea, [no-blur]";function f(){var e=document;var t=true;var n=false;function r(){n=true}function a(){t=true}function o(r){if(n){n=false;return}var a=e.activeElement;if(!a){return}if(a.matches(s)){return}var o=r.target;if(o===a){return}if(o.matches(s)||o.closest(s)){return}t=false;setTimeout(function(){if(!t){a.blur()}},50)}e.addEventListener("ionScrollStart",r);e.addEventListener("focusin",a,true);e.addEventListener("touchend",o,false);return function(){e.removeEventListener("ionScrollStart",r,true);e.removeEventListener("focusin",a,true);e.removeEventListener("touchend",o,false)}}var v=.3;function c(e,t,n){var r=e.closest("ion-item,[ion-item]")||e;return l(r.getBoundingClientRect(),t.getBoundingClientRect(),n,e.ownerDocument.defaultView.innerHeight)}function l(e,t,n,r){var a=e.top;var o=e.bottom;var i=t.top;var u=Math.min(t.bottom,r-n);var s=i+15;var f=u*.5;var c=f-o;var l=s-a;var d=Math.round(c<0?-c:l>0?-l:0);var m=Math.min(d,a-i);var p=Math.abs(m);var E=p/v;var g=Math.min(400,Math.max(150,E));return{scrollAmount:m,scrollDuration:g,scrollPadding:n,inputSafeY:-(a-s)+4}}function d(e,n,r,o){var i;var u=function(e){i=t(e)};var s=function(u){if(!i){return}var s=t(u);if(!p(6,i,s)&&!a(n)){u.preventDefault();u.stopPropagation();m(e,n,r,o)}};e.addEventListener("touchstart",u,true);e.addEventListener("touchend",s,true);return function(){e.removeEventListener("touchstart",u,true);e.removeEventListener("touchend",s,true)}}function m(e,t,n,a){var o=c(e,n,a);if(Math.abs(o.scrollAmount)<4){t.focus();return}r(e,t,true,o.inputSafeY);t.focus();n.scrollByPoint(0,o.scrollAmount,o.scrollDuration).then(function(){r(e,t,false,o.inputSafeY);t.focus()})}function p(e,t,n){if(t&&n){var r=t.x-n.x;var a=t.y-n.y;var o=r*r+a*a;return o>e*e}return false}var E="$ionPaddingTimer";function g(e){var t=document;function n(t){h(t.target,e)}function r(e){h(e.target,0)}t.addEventListener("focusin",n);t.addEventListener("focusout",r);return function(){t.removeEventListener("focusin",n);t.removeEventListener("focusout",r)}}function h(e,t){if(e.tagName!=="INPUT"){return}if(e.parentElement&&e.parentElement.tagName==="ION-INPUT"){return}if(e.parentElement&&e.parentElement.parentElement&&e.parentElement.parentElement.tagName==="ION-SEARCHBAR"){return}var n=e.closest("ion-content");if(n===null){return}var r=n[E];if(r){clearTimeout(r)}if(t>0){n.style.setProperty("--keyboard-offset",t+"px")}else{n[E]=setTimeout(function(){n.style.setProperty("--keyboard-offset","0px")},120)}}var L=true;var y=true;function S(e){var t=document;var n=e.getNumber("keyboardHeight",290);var r=e.getBoolean("scrollAssist",true);var a=e.getBoolean("hideCaretOnScroll",true);var o=e.getBoolean("inputBlurring",true);var i=e.getBoolean("scrollPadding",true);var s=new WeakMap;var v=new WeakMap;function c(e){var t=(e.shadowRoot||e).querySelector("input")||(e.shadowRoot||e).querySelector("textarea");var o=e.closest("ion-content");if(!t){return}if(!!o&&a&&!s.has(e)){var i=u(e,t,o);s.set(e,i)}if(!!o&&r&&!v.has(e)){var i=d(e,t,o,n);v.set(e,i)}}function l(e){if(a){var t=s.get(e);if(t){t()}s.delete(e)}if(r){var t=v.get(e);if(t){t()}v.delete(e)}}if(o&&L){f()}if(i&&y){g(n)}var m=Array.from(t.querySelectorAll("ion-input, ion-textarea"));for(var p=0,E=m;p<E.length;p++){var h=E[p];c(h)}t.body.addEventListener("ionInputDidLoad",function(e){c(e.target)});t.body.addEventListener("ionInputDidUnload",function(e){l(e.target)})}}}});