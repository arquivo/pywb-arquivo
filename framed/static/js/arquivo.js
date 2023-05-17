String.prototype.replaceAll = String.prototype.replaceAll || function(needle, replacement) {
    return this.split(needle).join(replacement);
}; 
/*Arquivo.pt specific functions and js code, such as loading constants, cookies, custom html code, etc*/
var ARQUIVO = ARQUIVO || (function(){
    var _static_path;
	var	_url;
	var _ts;
	var _hostname = window.location.hostname;
	var _language ='pt';
	var _patching = '';
	var _screenshotEndpoint;
	var _host_prefix;
	var _replayWithOldBrowsers;
	var _arquivoWebAppUrl;

	function isEmpty(val){
	    return (val === undefined || val == null || val.length <= 0) ? true : false;
	}

    return {
        init : function(host_prefix, static_path, screenshotEndpoint, patching, buildUrlSuffix, replayWithOldBrowsers, arquivoWebAppUrl) {
        	_buildUrlSuffix = buildUrlSuffix;
			_static_path = static_path;
			this.loadLanguage();
        	_screenshotEndpoint = screenshotEndpoint;
        	_host_prefix = host_prefix;
        	_patching = patching;
        	_replayWithOldBrowsers = replayWithOldBrowsers;
        	_arquivoWebAppUrl = arquivoWebAppUrl;

        	// fallback when pywb don't call the updateInfo function after the list of versions iframe.
        	window.addEventListener("load", function(event) {
        		ARQUIVO.updatePageOnUrlSearch(_url, _ts);
        	});
        },

        /**
         * get other archives URL
         */
        getOtherArchivesURL : function() {
        	return 'https://web.archive.org/web/' +_ts + '/' + _url;
        },
        getPatchingPageURL : function() {
        	return '/services/complete-page?url=' + encodeURIComponent(_url) + '&timestamp=' + _ts ;
        },
        getReplayWithOldBrowsersURL : function () {
        	return 'http://oldweb.today?browser=ff10' + '#' + 'https://arquivo.pt/noFrame/replay/' + _ts + '/' + _url;
        },
        
        /*
         * Choose language and load corresponding Constants
         */
		loadLanguage: function(){
			var language = $.cookie('i18n');
			if(!!language){
				language = language.split('_')[0].toUpperCase();
				localStorage.language = language;
			}
			language = localStorage.language;
			language = language == 'EN' ? 'EN' : 'PT';
			_language = language.toLowerCase();
		    document.write('<script type="text/javascript" language="JavaScript" src="'+_static_path+'/properties/Constants'+language+'.js'+_buildUrlSuffix+'"><\/script>');
		},

		/*
		 * Resize the replay_iframe
		 */
		iframeResize: function(){ /*Code written by the author of Jquery to dynamically resize iframe to always have height equal to the parent container*/
			var buffer = 20; //scroll bar buffer
			var overlayBuffer = 27 // overlay current style with a curve in the replaybar
			var iframe = document.getElementById('replay_iframe');
	

			function pageY(elem) {
			    return elem.offsetParent ? (elem.offsetTop + pageY(elem.offsetParent)) : elem.offsetTop;
			}

			function resizeIframe() {
			    var height = document.documentElement.clientHeight;
			    height -= pageY(document.getElementById('replay_iframe'))+ buffer+ overlayBuffer ;
			    height = (height < 0) ? 0 : height;
			    document.getElementById('replay_iframe').style.height = height+ buffer +overlayBuffer + 'px';
			}

			// .onload doesn't work with IE8 and older.
			if (iframe.attachEvent) {
			    iframe.attachEvent("onload", resizeIframe);
			} else {
			    iframe.onload=resizeIframe;
			}

			window.onresize = resizeIframe;    			
		},
		/**
		 * Write custom html code before the Iframe
		 */
		beforeIframe: function(){
			document.write(''+
			  '<div id="swipeContainer" class="swiper-container swiper-container-horizontal noprint">'+
			  ' <div class="swiper-wrapper" id="swiperWrapper">'+
			  '  <div class="swiper-slide content swiper-slide-active">'+
			  '    <div class="main-content">'+
			  '      <div class="container-fluid">'+
			  '        <div class="row text-center logo-main-div-no-border">'+
			  '                    <a class="logo-menu-anchor" href="/?l='+_language+'"><img src="'+_static_path+'/img/arquivo-logo-white.svg  " id="arquivoLogo" alt="Logo Arquivo.pt" class="text-center logo-main"></a>'+
			  '                    <a class="pull-left main-menu" id="menuButton"><div class="menu-button"><div class="bar"></div><div class="bar"></div><div class="bar"></div></div><span class="headerMenuText">'+Content.header.menu+'</span></a>'+
			  '                    <button id="replayMenuButton" " class="select-language" title="Replay menu"><span class="headerOptionsText">'+Content.header.options+'</span><span class="headerOptionsTextDots">...</span></button>'+
			  '        </div>  '+
			  '      </div>  '+
	'<div class="curve-background"></div>'+
	'<div class="background-top-curve"><p><a id="headerUrl" class="headerUrl" target="_blank"></a><span id="headerTimestamp" class="headerTimestamp"></span></p></div>');
		},
		afterIframe: function(){
			document.write(''+
			  '   </div>' +
              '   <div id="mainMask" class="maskMenu"></div>'+
              '  </div>'+
              '  <div class="swiper-slide replayMenu swiper-slide-next">'+
              '			<div class="main-menu-top-div">'+
			  '	 			<h4 id="menuUrl" title="'+_url+'">'+ _url +'</h4>' + 
			  ' 			<button href="#" onclick="ARQUIVO.goToContent()" class="close-functions clean-button-no-fill" id="closeSpecPopUp">&#10005;</button>' +			  
			  ' 			<h5 id="menuTs">'+ this.formatTimestampToPresentation(_ts) +'</h5>' + 			                             
			  '			</div>'+
			  '			<a href="'+_arquivoWebAppUrl+'/page/search?l='+Content.language+'&query='+encodeURIComponent(_url)+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ListVersionsClick\');"><h4><i class="fa fa-list" aria-hidden="true"></i> '+Content.allVersions+'</h4></a>'+ 						                      
			  ' 		<a href="#" id="a_moreinfo" title="'+Content.moreInfoIcon+'"><h4><i class="fa fa-info-circle right-9" aria-hidden="true"></i> '+Content.moreInfoIcon+'</h4></a>'+			  
              ' 		<a id="screenshotOption"><h4><i class="fa fa-camera right-5" aria-hidden="true"></i> '+Content.saveImage+'</h4></a>' +
			  '	 		<a id="printOption"><h4><i class="fa fa-print right-7" aria-hidden="true"></i> '+Content.print+'</h4></a>'+
              '			<a id="a_reconstruct" alt="'+Content.completePage+'" href=javascript:void(0) onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'Complete Page\'); ARQUIVO.attachCompletePageModal(); return false;"><h4><i class="complete-page"></i>'+Content.completePage+'</h4></a>'+
			  '		 	<a id="expandPage" href="/noFrame/replay/'+_ts+'/'+_url+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ExpandClick\');"><i class="fa fa-expand" aria-hidden="true"></i><span style="padding-left: 13px !important;">'+Content.expandPage+'</span></a>'+
			  (this.isReplayWithOldBrowsers() ?
			  '			<a id="replayWithOldBrowsers" alt="'+Content.replayWithOldBrowsers+'" href=javascript:void(0) onclick="ARQUIVO.replayWithOldBrowsers(); return false;"><h4><i class="replay-with-old-browsers"></i>'+Content.replayWithOldBrowsers+'</h4></a>':
			  ''
              )+
              '  </div>'+
              '	</div>'+
			  '</div>'+
			  '<div id="divPrintMe"></div>');
			this.attachScreenshotModal();
			this.attachPrintModal();
			this.iframeResize();
			this.createSlideMenu();
			this.attachShare();
			this.attachTools();
			this.attachMoreInfoModal();
			this.attachCompletepage();
			this.attachKeyBoardEvent();
 		},
 		goToContent: function(){
 			const mySwiper = document.querySelector('.swiper-container').swiper;
 			mySwiper.slideTo(1);
 		},
 		copyLink: function(){
			var dummy = document.createElement('input')	    
			var urlToCopy= window.location.href;

			document.body.appendChild(dummy);
			dummy.value = urlToCopy;
			dummy.select();
			document.execCommand('copy');
			document.body.removeChild(dummy);
			$('body').append('<div id="alertCopy" class="alert alert-success alertCopy"><strong>'+Content.linkCopied+'</strong></div>');
			$('#alertCopy').show().delay(1500).fadeOut();
			setTimeout(function(){
  			$('#alertCopy').remove();
			}, 2000); /*time to show the notification plus the time to do the fadeout effect*/ 			
 		},
 		attachCompletePageModal: function(){
 			ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'Complete Page');

		  	var message = this.isPatching() ? Content.completePageUsingPatchingConfirmationMessage : Content.leavingArquivo;

		  	var classModalTitle = "";
		  	if(_language === 'pt')
		  		classModalTitle = "completePageIcon";
		  	else
		  		classModalTitle = "completePageIconEN";
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content: '<h4 class="modalTitleComplete" id="'+classModalTitle+'">'+message+'</h4>' +
		              '<div class="row"><a id="completePage" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});               
		  	this.attachCompletepage();
		  	this.attachClosePopup();
		},
		isPatching : function() {
			return _patching.toLowerCase( ) === 'true';
		},
		attachCompletepage: function(){
		    $('#completePage').on('click', function(e){
		        ARQUIVO.sendEventToAnalytics('Complete Page', 'Clicked complete page and confirmed');

		        if (ARQUIVO.isPatching()) {
		        	// go to patching page
		        	window.open(ARQUIVO.getPatchingPageURL());
		        } else {
		        	// open other window with other archive URL
		        	window.open(ARQUIVO.getOtherArchivesURL());
		        }
		        ARQUIVO.closeUglipop();
		    });    
		},
		attachClosePopup: function(){
		  $('#cancelPopup').on('click', function(e){
		    ARQUIVO.closeUglipop();
		  });
		},
		closeUglipop: function(){
		  $('#uglipop_content_fixed').fadeOut();
		  $('#uglipop_overlay').fadeOut('fast');
		},
		replayWithOldBrowsers: function() {
			ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'Replay with old browser');
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content: '<h4 class="modalTitleReplayWithOldBrowsers">'+Content.leavingArquivoToReplayWithOldBrowsers+'</h4>' +
		              '<div class="row"><a id="okReplayWithOldBrowsers" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});               
		  	this.attachReplayWithOldBrowsers();
		  	this.attachClosePopup();
		},
		attachReplayWithOldBrowsers: function() {
			$('#okReplayWithOldBrowsers').on('click', function(e) {
		        ARQUIVO.sendEventToAnalytics('Replay with old browser', 'Clicked replay with old browser and confirmed');
		        window.open( ARQUIVO.getReplayWithOldBrowsersURL() );
		        ARQUIVO.closeUglipop();
		    });
		},
		// present url without protocol neither www.
		formatURLForPresentation: function(url) {
			return url.replace(/^(http(s)?\:\/\/)?(www\.)?/,'').replace(/\/$/,'');
		},
 		updateInfo: function(url, ts){
 			_url = url;
 			_ts = ts;
			/*get new page title and update it*/  
			var title = $("#replay_iframe").contents().find("meta[property='og:title']").attr("content");
			if(title === undefined || title === null) // there is no og:title meta tag in this iframe
			{
			  title = $("#replay_iframe").contents().find("title").html(); //search for a title tag in the iframe
			  if (title === undefined || !title.length){ //there is no title 
			      title = "Arquivo.pt"/*Content.shareMessage;*/
			  }
			}
			title = title + Content.preservedByArquivo;
			document.title = title;

			var addthis_config = addthis_config||{};
			addthis_config.data_track_addressbar = false;
			addthis_config.data_track_clickback = false;

			$('#expandPage').attr('href', '/noFrame/replay/'+_ts+'/'+_url);
			$('#expandPage').attr('onclick', 'ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ExpandClick\')');

			$('#menuUrl').attr('title', _url);
			$('#menuUrl').html(_url); /*update menu url*/
			$('#headerUrl').attr('href', _url).attr('title', _url).html(this.formatURLForPresentation(_url)); // add url of the page on header without protocol neither www.
			$('#headerTimestamp').html(ARQUIVO.formatTimestampToPresentation(_ts));
			$('#menuTs').html(ARQUIVO.formatTimestampToPresentation(_ts)); /*update menu ts*/
			$('#tableVersionsSideLink').attr('href', _arquivoWebAppUrl+'/page/search?viewMode=table&l='+Content.language+'&query='+encodeURIComponent(_url));
			$('#a_reconstruct').attr('href', this.getPatchingPageURL());
			$('#replayWithOldBrowsers').attr('href', this.getReplayWithOldBrowsersURL());
			
			const replayMenuButton = document.getElementById("replayMenuButton");
			if (replayMenuButton) {
				replayMenuButton.style.display = "block";
			}

			ARQUIVO.updatePageOnUrlSearch(url, ts);
			gtag('event', 'wayback_view', {
				wayback_page_title: title,
				wayback_page_location: _url  
			  });
 		},
 		createSlideMenu: function(){

 			this.insertMenuHtlm();

		    var replayMenu = document.querySelector('#replayMenuButton');
		    var openReplayMenu = function () {
		      swiper.slideNext();
		      $('#mainMask').fadeIn('fast');
		    };

		    var menuButton = document.querySelector('#menuButton');
		    var openMenu = function () {
		      swiper.slidePrev();
		    };
		    swiper = new Swiper('.swiper-container', {
		      slidesPerView: 'auto',
		      initialSlide: 1,
		      resistanceRatio: 0,
		      slideToClickedSlide: true,
		      on: {
		        slideChangeTransitionStart: function () {
		          var slider = this;
		          if (slider.activeIndex === 0) { /*open menu*/
		          	$('#mainMask').fadeIn('fast');
		            menuButton.classList.add('open');
		            $('.swiper-container').removeClass('swiper-no-swiping');
		            // required because of slideToClickedSlide
		            menuButton.removeEventListener('click', openMenu, true);
		          } else  if (slider.activeIndex === 1) { /*close menu*/
		          	$('.swiper-container').addClass('swiper-no-swiping');
		          	$('#mainMask').fadeOut('fast');
		            menuButton.classList.remove('open');
		          
		          // can not make ionic return the replay menu has activeIndex with 2 value, so the following if dead code.
		          } else if(slider.activeIndex === 2){
		          	$('#mainMask').fadeIn('fast');
		          }
		        }
		        , slideChangeTransitionEnd: function () {
		          var slider = this;
		          if (slider.activeIndex === 1) {
		            menuButton.addEventListener('click', openMenu, true);
		            replayMenu.addEventListener('click', openReplayMenu, true);
		          }		         
		        },
		      }
		    });
		    swiper.allowSlidePrev = true;
		    swiper.allowSlideNext = true;
 		},

 		insertMenuHtlm: function(){
 			$('.swiper-wrapper').prepend(
			  '		  <div class="swiper-slide menu swiper-slide-prev">' +
			  		   '<div class="main-menu-top-div">'+
			  		   	 '<h4>&nbsp;</h4>'+
			  	         '<button href="#" onclick="ARQUIVO.goToContent()" class="close-functions clean-button-no-fill">&#10005;</button>' +
			  	       '</div>'+
              '		 	<a id="changeLanguage" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ChangeLanguageTo'+Content.otherLanguage+'Click\');" href="/switchlang?l='+Content.language.toLowerCase()+'"><h4><i class="fa fa-flag right-6" aria-hidden="true"></i> '+Content.otherLanguageExtended+'</h4></a>'+
			  '			<button class="clean-button" onclick="ARQUIVO.copyLink();"><h4><i class="fa fa-link padding-right-menu-icon" aria-hidden="true"></i> '+Content.copyLink+'</h4></button>' +
  					   '<button class="clean-button" id="pagesMenu" onclick="ARQUIVO.pagesClick();"><h4><i class="fa fa-globe padding-right-menu-icon" aria-hidden="true"></i> '+Content.pages+'<i id="pagesCarret" class="fa fa-caret-down iCarret shareCarret pull-right" aria-hidden="true"></i></h4></button>'+	 			  
      				   '<div id="pageOptions">'+
              ' 			<a href="'+_arquivoWebAppUrl+'/page/search?l='+Content.language+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'NewSearchClick\');"><h4 class="submenu"><i class="fa fa-search right-7" aria-hidden="true"></i> '+Content.newSearch+'</h4></a>' +
              ' 			<a href="'+_arquivoWebAppUrl+'/page/advanced/search?l='+Content.language+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'AdvancedSearchClick\');"><h4 class="submenu"><i class="fa fa-search-plus right-7" aria-hidden="true"></i> '+Content.advancedSearch+'</h4></a>' +
              		   '</div>'+
			  		   '<button class="clean-button" id="imagesMenu" onclick="ARQUIVO.imagesClick();"><h4><i class="fa fa-image padding-right-menu-icon" aria-hidden="true"></i> '+Content.images+'<i id="imagesCarret" class="fa iCarret shareCarret pull-right fa-caret-down" aria-hidden="true"></i></h4></button>'+
      				   '<div id="imageOptions">'+
              ' 			<a href="'+_arquivoWebAppUrl+'/image/search?l='+Content.language+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'NewImageSearchClick\');"><h4 class="submenu"><i class="fa fa-search right-7" aria-hidden="true"></i> '+Content.newSearch+'</h4></a>' +
              ' 			<a href="'+_arquivoWebAppUrl+'/image/advanced/search?l='+Content.language+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'AdvancedImageSearchClick\');"><h4 class="submenu"><i class="fa fa-search-plus right-7" aria-hidden="true"></i> '+Content.advancedSearch+'</h4></a>' +
              		   '</div>'+                
              '         <a href="'+Content.recordHref+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'RecordClick\');"><h4><i class="fa fa-video-camera" aria-hidden="true"></i>'+Content.recordPages+'</h4></a>'+
              '		 	<a href="'+Content.aboutHref+'" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'AboutClick\');"><h4><i class="fa fa-info-circle right-10" aria-hidden="true"></i> '+Content.about+'</h4></a>'+
			  '		</div>' ); 			
 		},

 		attachScreenshotModal: function(){
		  $('#screenshotOption').on('click', function(e){
		  	ARQUIVO.closeSwipeMenu();    		  	
		  	ARQUIVO.screenshotModal();		  	
		  }); 			
 		}, 		
 		/*When user clicks on the screenshot link generate screenshot of current url*/
 		attachScreenshot: function(){
		  $('#takeScreenshot').on('click', function(e){
		  	ARQUIVO.closeUglipop();
		    window.open('//'+_hostname+'/screenshot/?url='+encodeURIComponent("https://"+_hostname+"/noFrame/replay/"+ _ts+'/'+_url)+"&width="+window.screen.width/*window.innerWidth*/+"&height="+/*window.innerHeight*/ window.screen.height);
		  }); 			
 		},
 		attachPrintModal: function(){
		  $('#printOption').on('click', function(e){
		  	ARQUIVO.closeSwipeMenu();    		  	
		  	ARQUIVO.printModal();
		  }); 			
 		}, 
 		attachPrint: function(){
		  $('#printPage').on('click', function(e){
		    ARQUIVO.getImageToPrint("https://"+_hostname+"/noFrame/replay/"+ _ts+"/"+encodeURIComponent(_url));
		  }); 			
 		},  		 		 				
 		attachShare: function(){
		  $('#shareMenu').on('click', function(e){
		  	ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'ShareMenuClick');
		    $('#shareCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#shareOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	
 		attachTools: function(){
		  $('#toolsMenu').on('click', function(e){
		  	ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'ToolsMenuClick');
		    $('#toolsCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#toolsOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	 			
		moreInfoModal: function(){
		    ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'MoreInformationMenuClick');
		    var requestURL = "//"+window.location.hostname.replace("m.","")+ "/textsearch";
		    metadataResponse= '';
		      $.ajax({
		      // example request to the cdx-server api - 'http://arquivo.pt/textsearch?metadata=http%3A%2F%2Fquiz.musicbox.sapo.pt%2F%2F20131108093638'
		          url: requestURL,
		          data: {
		            metadata: _url+"/"+_ts
		          },
		          dataType: 'text',

		        error: function() {
		             printLoading= false; 
		             console.log('error showing metadata');
		         },
		         success: function(data) {
		              var theMetadata = jQuery.parseJSON(data).response_items;
		              for(var obj in theMetadata){
		                  if(theMetadata.hasOwnProperty(obj)){
		                    for(var prop in theMetadata[obj]){
		                        if(theMetadata[obj][prop] === '') continue; /*do not show empty fields*/
		                        if(theMetadata[obj].hasOwnProperty(prop)){
		                          if(typeof(theMetadata[obj][prop]) === 'string' && theMetadata[obj][prop].startsWith('http')){
		                            metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: <a target=_blank href="'+theMetadata[obj][prop]+'">' + theMetadata[obj][prop] + '</a></p>';    
		                          }
		                          else if(prop == "collection"){
		                            metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: <a target=_blank href="https://arquivo.pt/colecoes">' + theMetadata[obj][prop] + '</a></p>';
		                          }
		                          else{
		                           metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: ' + theMetadata[obj][prop] + '</p>';
		                          }
		                        }
		                    }
		                  }
		              }            

		              uglipop({
		                class:'modalReplay noprint scrollModal PageSpec', //styling class for Modal
		                source:'html',
		                content:'<button id="removeModal" class="expand__close" title="Fechar"></button>'+
		                        '<h4 class="modalTitle"><i  alt="'+Content.moreInfoIcon+'" class="ion ion-information-circled menu-icon removeContentIcon"></i> '+Content.moreInfoIcon+' <a target="_blank" href="https://github.com/arquivo/pwa-technologies/wiki/Arquivo.pt-API#response-fields">'+Content.techDetails+'</a></h4>'+
		                        '<div>' + metadataResponse + '</div>'
		              });
		              ARQUIVO.attachRemoveModal();
		              $( ".scrollModal" ).ready(function() {
		                $( ".scrollModal" ).parent().css({
		                    'top': '2%',
		                    'left': '3%',
		                    'bottom': '1%',
		                    'width': '94%',
		                    'height': '96%', 
		                    'overflow': 'auto' ,
		                    'transform': 'none',
		                    '-webkit-transform': 'none',
		                    '-ms-transform': 'unset'
		                });

		              }); 
		              loadedModal = true;
		         },
		         type: 'GET',
		      });   
		}, 		
		attachMoreInfoModal: function(){
       		$('#a_moreinfo').on('click', function(e){         
        		ARQUIVO.moreInfoModal();        
      		});    			
		},
		attachRemoveModal: function(){
		       $('#removeModal').on('click', function(e){    
		          ARQUIVO.closeUglipopCustomCss();  
		        });
		       $('#uglipop_overlay').on('click', function(e){
		          if( $('#uglipop_popbox').hasClass('scrollModal')){
		            ARQUIVO.closeUglipopCustomCss();
		          }
		       });    
		},
		closeUglipopCustomCss: function(){
		  $('#uglipop_content_fixed').hide();
		  $('#uglipop_overlay').hide();
		  $( "#uglipop_content_fixed" ).css({
		                  'top': '50%',
		                  'left': '50%',
		                  'bottom': '',
		                  'width': '',
		                  'height': '', 
		                  'opacity': '1',  
		                  'overflow': 'auto' ,
		                  'transform': 'translate(-50%, -50%)',
		                  '-webkit-transform': 'translate(-50%, -50%)',
		                  '-ms-transform': 'translate(-50%, -50%)'
		  });
		},
		
		/**
		 * Returns current timestamp in short form such as '2 Nov 10:24, 2015'
		 */
		formatTimestampToPresentation: function(timestamp){
			var year = timestamp.substring(0, 4);
			var month = timestamp.substring(4, 6);
			var day = timestamp.substring(6, 8);
			if(day.charAt(0) == '0'){
				day = day.charAt(1);
			}
			var hour = timestamp.substring(8,10);
			var minute = timestamp.substring(10,12);

			return day+" "+Content.months[month]+" "+Content.at+" "+hour+"h"+minute+", "+year;
		},
		getDatets: function(){
		              var year = ts.substring(0, 4);
		              var month = ts.substring(4, 6);
		              var day = ts.substring(6, 8);
		              if(day.charAt(0) == '0'){
		                day = day.charAt(1);
		              }
		  return day+" "+ Content.months[month]+", "+year;
		},
		getImageToPrint: function(encodedURLToPrint){
			ARQUIVO.closeUglipop();
			ARQUIVO.loadingModal();

			var requestURL = _screenshotEndpoint + "?url=" + encodedURLToPrint + "&download=false";

			let divPrintMe = document.getElementById("divPrintMe");
			let imgElem = document.getElementById("imgToPrint");

			if (imgElem == null){
				imgElem = document.createElement('img');
				imgElem.setAttribute("id", "imgToPrint");
				imgElem.setAttribute("width", "600px");
				imgElem.style.display = 'inherited';
				divPrintMe.appendChild(imgElem);
			}

			imgElem.addEventListener('load', function() {
				setTimeout(function() {
					window.print();
				}, 1000);
			});

			imgElem.src = requestURL;
			divPrintMe.style.display = "block";

			ARQUIVO.loadingModal();
			console.log(this.url);
		},
		pagesClick: function(){
		    $('#pagesCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#pageOptions').slideToggle( "fast", "linear" );
		},
		imagesClick: function(){
		    $('#imagesCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#imageOptions').slideToggle( "fast", "linear" );
		},
		printModal: function(){
			ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'PrintMenuClick');
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-print" aria-hidden="true"></i> '+Content.printModalTitle+'</h4>'+
		              '<div class="row"><a id="printPage" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'PrintMenuConfirm\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'PrintMenuCancel\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachPrint();          			
		    this.attachClosePopup();
		},
		screenshotModal: function(){
			ARQUIVO.sendEventToAnalytics('ReplayBarFunctions', 'ScreenshotMenuClick');
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-camera" aria-hidden="true"></i> '+Content.saveAsImage+'</h4>'+
		              '<div class="row"><a id="takeScreenshot" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ScreenshotMenuConfirm\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ARQUIVO.sendEventToAnalytics(\'ReplayBarFunctions\', \'ScreenshotMenuCancel\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachScreenshot();          			
		    this.attachClosePopup();
		},
		loadingModal: function(){
			$('.maskMenu').toggle();
			$('#loadingAnimation').toggle();
		},		
		closeUglipop: function(){
			$('#uglipop_content_fixed').fadeOut();
			$('#uglipop_overlay').fadeOut('fast');
		},
 		attachClosePopup: function(){
		  $('#cancelPopup').on('click', function(e){
		  	ARQUIVO.closeUglipop();
		  }); 	 			
 		},
		closeSwipeMenu: function(){
		},
		
		/**
		 * When the user press Esc key on keyboard go to primary content.
		 */
		attachKeyBoardEvent: function() {
			if (document.onkeydown == null) {
				document.onkeydown = function(evt) {
				  // When pressing escape key close image
				  var isEscape = false;
				  if ("key" in evt) {
				      isEscape = (evt.key === "Escape" || evt.key === "Esc");
				  } else {
				      isEscape = (evt.keyCode === 27);
				  }
				  if (isEscape) {
				      ARQUIVO.goToContent();
				  }
				}
			}
		},
        
        /**
         * Called from url search iframe when the user clicks a specific version
         * the message is the url clicked
         */
		urlSearchClickOnVersion: function(waybackUrlClicked) {
			const timestampAndURL = waybackUrlClicked.substring(wbinfo.prefix.length);
			const timestampURLSeparatorPos = timestampAndURL.indexOf('/');
			const timestamp = timestampAndURL.substring(0, timestampURLSeparatorPos);
			const url = timestampAndURL.substring(timestampURLSeparatorPos+1);
			var frameSrc = wbinfo.prefix + timestamp + 'mp_/' + url;
			$('#replay_iframe').attr('src', frameSrc); //update the iframe to the new version
		},
	    
	    /**
	     * Function to be called to update the current url on list of view iframe that is on left of the screen.
	     */
	    updatePageOnUrlSearch: function(url, timestamp) {
	    	function getIframeWindow(iframe_object) {
			  var doc;

			  if (iframe_object.contentWindow) {
			    return iframe_object.contentWindow;
			  }

			  if (iframe_object.window) {
			    return iframe_object.window;
			  } 

			  if (!doc && iframe_object.contentDocument) {
			    doc = iframe_object.contentDocument;
			  } 

			  if (!doc && iframe_object.document) {
			    doc = iframe_object.document;
			  }

			  if (doc && doc.defaultView) {
			   return doc.defaultView;
			  }

			  if (doc && doc.parentWindow) {
			    return doc.parentWindow;
			  }

			  return undefined;
			}

			function doUpdate(iframeId, url, timestamp) {
				// https://arquivo.pt/partials/replay-nav?url=http%3A%2F%2Fwww.sapo.pt%2F&timestamp=20080314154859
				const l = localStorage.language == 'EN' ? 'en' : 'pt';

				const ajaxUrl = '/partials/replay-nav?url=' + encodeURIComponent( url ) + '&timestamp=' + timestamp + '&l=' + l;
				$.ajax({
					url: ajaxUrl,
					error: function () {
						printLoading = false;
						console.log('error fetching timestamps');
					},
					type: 'GET',
					success: function (data) {
						const element = $(data);
						element.find('#replay-table').remove();
						element.find('#replay-list').remove();
						$('#replay-left-nav').html('').append(element);
					},
				});


				// const ifrm_el = document.getElementById(iframeId);
				// if (ifrm_el) {
				// 	const ifrm_win = getIframeWindow(ifrm_el);
				// 	if (ifrm_win && ifrm_win.replacePageAndHighlightTimestamp) { // the function could be not defined because the iframe could be starting up.
				// 		ifrm_win.replacePageAndHighlightTimestamp(url, timestamp);
				// 	}
				// }
			}
			doUpdate("url_search_iframe", url, timestamp);
		},

	    /**
	     * Send event to google analytics where the eventLabel by default is like arquivo.pt/<timestamp>/<url>
	     */
	    sendEventToAnalytics: function(eventCategory, eventAction, eventLabel) {
	    	eventLabel = eventLabel || "arquivo.pt/" + _ts + '/' +_url;
			gtag("event", eventCategory, {
				"action": eventAction, 
				"label": eventLabel 
			} );
	    },

		isReplayWithOldBrowsers : function() {
			return _replayWithOldBrowsers.toLowerCase( ) === 'true' || isEmpty(_replayWithOldBrowsers);
		},

    };
}());

