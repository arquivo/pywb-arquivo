'use strict';

Object.defineProperty(exports, '__esModule', { value: true });

const __chunk_1 = require('./chunk-8de9033d.js');
require('./chunk-d8847c1c.js');
require('./chunk-e9c8ab68.js');
const __chunk_4 = require('./chunk-6d671032.js');
const __chunk_5 = require('./chunk-9c9fbda4.js');
const __chunk_9 = require('./chunk-1b4d0f1d.js');
const __chunk_10 = require('./chunk-e77bed2a.js');

/**
 * iOS Popover Enter Animation
 */
function iosEnterAnimation(AnimationC, baseEl, ev) {
    let originY = 'top';
    let originX = 'left';
    const contentEl = baseEl.querySelector('.popover-content');
    const contentDimentions = contentEl.getBoundingClientRect();
    const contentWidth = contentDimentions.width;
    const contentHeight = contentDimentions.height;
    const bodyWidth = baseEl.ownerDocument.defaultView.innerWidth;
    const bodyHeight = baseEl.ownerDocument.defaultView.innerHeight;
    // If ev was passed, use that for target element
    const targetDim = ev && ev.target && ev.target.getBoundingClientRect();
    const targetTop = targetDim != null && 'top' in targetDim ? targetDim.top : bodyHeight / 2 - contentHeight / 2;
    const targetLeft = targetDim != null && 'left' in targetDim ? targetDim.left : bodyWidth / 2;
    const targetWidth = (targetDim && targetDim.width) || 0;
    const targetHeight = (targetDim && targetDim.height) || 0;
    const arrowEl = baseEl.querySelector('.popover-arrow');
    const arrowDim = arrowEl.getBoundingClientRect();
    const arrowWidth = arrowDim.width;
    const arrowHeight = arrowDim.height;
    if (targetDim == null) {
        arrowEl.style.display = 'none';
    }
    const arrowCSS = {
        top: targetTop + targetHeight,
        left: targetLeft + targetWidth / 2 - arrowWidth / 2
    };
    const popoverCSS = {
        top: targetTop + targetHeight + (arrowHeight - 1),
        left: targetLeft + targetWidth / 2 - contentWidth / 2
    };
    // If the popover left is less than the padding it is off screen
    // to the left so adjust it, else if the width of the popover
    // exceeds the body width it is off screen to the right so adjust
    //
    let checkSafeAreaLeft = false;
    let checkSafeAreaRight = false;
    // If the popover left is less than the padding it is off screen
    // to the left so adjust it, else if the width of the popover
    // exceeds the body width it is off screen to the right so adjust
    // 25 is a random/arbitrary number. It seems to work fine for ios11
    // and iPhoneX. Is it perfect? No. Does it work? Yes.
    if (popoverCSS.left < POPOVER_IOS_BODY_PADDING + 25) {
        checkSafeAreaLeft = true;
        popoverCSS.left = POPOVER_IOS_BODY_PADDING;
    }
    else if (contentWidth + POPOVER_IOS_BODY_PADDING + popoverCSS.left + 25 > bodyWidth) {
        // Ok, so we're on the right side of the screen,
        // but now we need to make sure we're still a bit further right
        // cus....notchurally... Again, 25 is random. It works tho
        checkSafeAreaRight = true;
        popoverCSS.left = bodyWidth - contentWidth - POPOVER_IOS_BODY_PADDING;
        originX = 'right';
    }
    // make it pop up if there's room above
    if (targetTop + targetHeight + contentHeight > bodyHeight && targetTop - contentHeight > 0) {
        arrowCSS.top = targetTop - (arrowHeight + 1);
        popoverCSS.top = targetTop - contentHeight - (arrowHeight - 1);
        baseEl.className = baseEl.className + ' popover-bottom';
        originY = 'bottom';
        // If there isn't room for it to pop up above the target cut it off
    }
    else if (targetTop + targetHeight + contentHeight > bodyHeight) {
        contentEl.style.bottom = POPOVER_IOS_BODY_PADDING + '%';
    }
    arrowEl.style.top = arrowCSS.top + 'px';
    arrowEl.style.left = arrowCSS.left + 'px';
    contentEl.style.top = popoverCSS.top + 'px';
    contentEl.style.left = popoverCSS.left + 'px';
    if (checkSafeAreaLeft) {
        contentEl.style.left = `calc(${popoverCSS.left}px + var(--ion-safe-area-left, 0px))`;
    }
    if (checkSafeAreaRight) {
        contentEl.style.left = `calc(${popoverCSS.left}px - var(--ion-safe-area-right, 0px))`;
    }
    contentEl.style.transformOrigin = originY + ' ' + originX;
    const baseAnimation = new AnimationC();
    const backdropAnimation = new AnimationC();
    backdropAnimation.addElement(baseEl.querySelector('ion-backdrop'));
    backdropAnimation.fromTo('opacity', 0.01, 0.08);
    const wrapperAnimation = new AnimationC();
    wrapperAnimation.addElement(baseEl.querySelector('.popover-wrapper'));
    wrapperAnimation.fromTo('opacity', 0.01, 1);
    return Promise.resolve(baseAnimation
        .addElement(baseEl)
        .easing('ease')
        .duration(100)
        .add(backdropAnimation)
        .add(wrapperAnimation));
}
const POPOVER_IOS_BODY_PADDING = 5;

/**
 * iOS Popover Leave Animation
 */
function iosLeaveAnimation(AnimationC, baseEl) {
    const baseAnimation = new AnimationC();
    const backdropAnimation = new AnimationC();
    backdropAnimation.addElement(baseEl.querySelector('ion-backdrop'));
    const wrapperAnimation = new AnimationC();
    wrapperAnimation.addElement(baseEl.querySelector('.popover-wrapper'));
    wrapperAnimation.fromTo('opacity', 0.99, 0);
    backdropAnimation.fromTo('opacity', 0.08, 0);
    return Promise.resolve(baseAnimation
        .addElement(baseEl)
        .easing('ease')
        .duration(500)
        .add(backdropAnimation)
        .add(wrapperAnimation));
}

/**
 * Md Popover Enter Animation
 */
function mdEnterAnimation(AnimationC, baseEl, ev) {
    const doc = baseEl.ownerDocument;
    const isRTL = doc.dir === 'rtl';
    let originY = 'top';
    let originX = isRTL ? 'right' : 'left';
    const contentEl = baseEl.querySelector('.popover-content');
    const contentDimentions = contentEl.getBoundingClientRect();
    const contentWidth = contentDimentions.width;
    const contentHeight = contentDimentions.height;
    const bodyWidth = doc.defaultView.innerWidth;
    const bodyHeight = doc.defaultView.innerHeight;
    // If ev was passed, use that for target element
    const targetDim = ev && ev.target && ev.target.getBoundingClientRect();
    // As per MD spec, by default position the popover below the target (trigger) element
    const targetTop = targetDim != null && 'bottom' in targetDim
        ? targetDim.bottom
        : bodyHeight / 2 - contentHeight / 2;
    const targetLeft = targetDim != null && 'left' in targetDim
        ? isRTL
            ? targetDim.left - contentWidth + targetDim.width
            : targetDim.left
        : bodyWidth / 2 - contentWidth / 2;
    const targetHeight = (targetDim && targetDim.height) || 0;
    const popoverCSS = {
        top: targetTop,
        left: targetLeft
    };
    // If the popover left is less than the padding it is off screen
    // to the left so adjust it, else if the width of the popover
    // exceeds the body width it is off screen to the right so adjust
    if (popoverCSS.left < POPOVER_MD_BODY_PADDING) {
        popoverCSS.left = POPOVER_MD_BODY_PADDING;
        // Same origin in this case for both LTR & RTL
        // Note: in LTR, originX is already 'left'
        originX = 'left';
    }
    else if (contentWidth + POPOVER_MD_BODY_PADDING + popoverCSS.left >
        bodyWidth) {
        popoverCSS.left = bodyWidth - contentWidth - POPOVER_MD_BODY_PADDING;
        // Same origin in this case for both LTR & RTL
        // Note: in RTL, originX is already 'right'
        originX = 'right';
    }
    // If the popover when popped down stretches past bottom of screen,
    // make it pop up if there's room above
    if (targetTop + targetHeight + contentHeight > bodyHeight &&
        targetTop - contentHeight > 0) {
        popoverCSS.top = targetTop - contentHeight - targetHeight;
        baseEl.className = baseEl.className + ' popover-bottom';
        originY = 'bottom';
        // If there isn't room for it to pop up above the target cut it off
    }
    else if (targetTop + targetHeight + contentHeight > bodyHeight) {
        contentEl.style.bottom = POPOVER_MD_BODY_PADDING + 'px';
    }
    contentEl.style.top = popoverCSS.top + 'px';
    contentEl.style.left = popoverCSS.left + 'px';
    contentEl.style.transformOrigin = originY + ' ' + originX;
    const baseAnimation = new AnimationC();
    const backdropAnimation = new AnimationC();
    backdropAnimation.addElement(baseEl.querySelector('ion-backdrop'));
    backdropAnimation.fromTo('opacity', 0.01, 0.32);
    const wrapperAnimation = new AnimationC();
    wrapperAnimation.addElement(baseEl.querySelector('.popover-wrapper'));
    wrapperAnimation.fromTo('opacity', 0.01, 1);
    const contentAnimation = new AnimationC();
    contentAnimation.addElement(baseEl.querySelector('.popover-content'));
    contentAnimation.fromTo('scale', 0.001, 1);
    const viewportAnimation = new AnimationC();
    viewportAnimation.addElement(baseEl.querySelector('.popover-viewport'));
    viewportAnimation.fromTo('opacity', 0.01, 1);
    return Promise.resolve(baseAnimation
        .addElement(baseEl)
        .easing('cubic-bezier(0.36,0.66,0.04,1)')
        .duration(300)
        .add(backdropAnimation)
        .add(wrapperAnimation)
        .add(contentAnimation)
        .add(viewportAnimation));
}
const POPOVER_MD_BODY_PADDING = 12;

/**
 * Md Popover Leave Animation
 */
function mdLeaveAnimation(AnimationC, baseEl) {
    const baseAnimation = new AnimationC();
    const backdropAnimation = new AnimationC();
    backdropAnimation.addElement(baseEl.querySelector('ion-backdrop'));
    const wrapperAnimation = new AnimationC();
    wrapperAnimation.addElement(baseEl.querySelector('.popover-wrapper'));
    wrapperAnimation.fromTo('opacity', 0.99, 0);
    backdropAnimation.fromTo('opacity', 0.32, 0);
    return Promise.resolve(baseAnimation
        .addElement(baseEl)
        .easing('ease')
        .duration(500)
        .add(backdropAnimation)
        .add(wrapperAnimation));
}

/**
 * @virtualProp {"ios" | "md"} mode - The mode determines which platform styles to use.
 */
class Popover {
    constructor(hostRef) {
        __chunk_1.registerInstance(this, hostRef);
        this.presented = false;
        this.mode = __chunk_1.getIonMode(this);
        /**
         * If `true`, the keyboard will be automatically dismissed when the overlay is presented.
         */
        this.keyboardClose = true;
        /**
         * If `true`, the popover will be dismissed when the backdrop is clicked.
         */
        this.backdropDismiss = true;
        /**
         * If `true`, a backdrop will be displayed behind the popover.
         */
        this.showBackdrop = true;
        /**
         * If `true`, the popover will be translucent.
         */
        this.translucent = false;
        /**
         * If `true`, the popover will animate.
         */
        this.animated = true;
        this.didPresent = __chunk_1.createEvent(this, "ionPopoverDidPresent", 7);
        this.willPresent = __chunk_1.createEvent(this, "ionPopoverWillPresent", 7);
        this.willDismiss = __chunk_1.createEvent(this, "ionPopoverWillDismiss", 7);
        this.didDismiss = __chunk_1.createEvent(this, "ionPopoverDidDismiss", 7);
    }
    onDismiss(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.dismiss();
    }
    onBackdropTap() {
        this.dismiss(undefined, __chunk_4.BACKDROP);
    }
    lifecycle(modalEvent) {
        const el = this.usersElement;
        const name = LIFECYCLE_MAP[modalEvent.type];
        if (el && name) {
            const event = new CustomEvent(name, {
                bubbles: false,
                cancelable: false,
                detail: modalEvent.detail
            });
            el.dispatchEvent(event);
        }
    }
    /**
     * Present the popover overlay after it has been created.
     */
    async present() {
        if (this.presented) {
            return;
        }
        const container = this.el.querySelector('.popover-content');
        if (!container) {
            throw new Error('container is undefined');
        }
        const data = Object.assign({}, this.componentProps, { popover: this.el });
        this.usersElement = await __chunk_9.attachComponent(this.delegate, container, this.component, ['popover-viewport', this.el['s-sc']], data);
        await __chunk_10.deepReady(this.usersElement);
        return __chunk_4.present(this, 'popoverEnter', iosEnterAnimation, mdEnterAnimation, this.event);
    }
    /**
     * Dismiss the popover overlay after it has been presented.
     *
     * @param data Any data to emit in the dismiss events.
     * @param role The role of the element that is dismissing the popover. For example, 'cancel' or 'backdrop'.
     */
    async dismiss(data, role) {
        const shouldDismiss = await __chunk_4.dismiss(this, data, role, 'popoverLeave', iosLeaveAnimation, mdLeaveAnimation, this.event);
        if (shouldDismiss) {
            await __chunk_9.detachComponent(this.delegate, this.usersElement);
        }
        return shouldDismiss;
    }
    /**
     * Returns a promise that resolves when the popover did dismiss.
     */
    onDidDismiss() {
        return __chunk_4.eventMethod(this.el, 'ionPopoverDidDismiss');
    }
    /**
     * Returns a promise that resolves when the popover will dismiss.
     */
    onWillDismiss() {
        return __chunk_4.eventMethod(this.el, 'ionPopoverWillDismiss');
    }
    hostData() {
        const mode = __chunk_1.getIonMode(this);
        return {
            'aria-modal': 'true',
            'no-router': true,
            style: {
                zIndex: 20000 + this.overlayIndex,
            },
            class: Object.assign({}, __chunk_5.getClassMap(this.cssClass), { [mode]: true, 'popover-translucent': this.translucent })
        };
    }
    __stencil_render() {
        return [
            __chunk_1.h("ion-backdrop", { tappable: this.backdropDismiss, visible: this.showBackdrop }),
            __chunk_1.h("div", { class: "popover-wrapper" }, __chunk_1.h("div", { class: "popover-arrow" }), __chunk_1.h("div", { class: "popover-content" }))
        ];
    }
    get el() { return __chunk_1.getElement(this); }
    render() { return __chunk_1.h(__chunk_1.Host, this.hostData(), this.__stencil_render()); }
    static get style() { return ".sc-ion-popover-ios-h{--background:var(--ion-background-color,#fff);--min-width:0;--min-height:0;--max-width:auto;--height:auto;left:0;right:0;top:0;bottom:0;display:-ms-flexbox;display:flex;position:fixed;-ms-flex-align:center;align-items:center;-ms-flex-pack:center;justify-content:center;color:var(--ion-text-color,#000);z-index:1000}.overlay-hidden.sc-ion-popover-ios-h{display:none}.popover-wrapper.sc-ion-popover-ios{opacity:0;z-index:10}.popover-content.sc-ion-popover-ios{display:-ms-flexbox;display:flex;position:absolute;-ms-flex-direction:column;flex-direction:column;width:var(--width);min-width:var(--min-width);max-width:var(--max-width);height:var(--height);min-height:var(--min-height);max-height:var(--max-height);background:var(--background);-webkit-box-shadow:var(--box-shadow);box-shadow:var(--box-shadow);overflow:auto;z-index:10}.popover-viewport.sc-ion-popover-ios{--ion-safe-area-top:0px;--ion-safe-area-right:0px;--ion-safe-area-bottom:0px;--ion-safe-area-left:0px}.sc-ion-popover-ios-h{--width:200px;--max-height:90%;--box-shadow:none}.popover-content.sc-ion-popover-ios{border-radius:10px}.popover-arrow.sc-ion-popover-ios{display:block;position:absolute;width:20px;height:10px;overflow:hidden}.popover-arrow.sc-ion-popover-ios:after{left:3px;top:3px;border-radius:3px;position:absolute;width:14px;height:14px;-webkit-transform:rotate(45deg);transform:rotate(45deg);background:var(--background);content:\"\";z-index:10}[dir=rtl].sc-ion-popover-ios-h .popover-arrow.sc-ion-popover-ios:after, [dir=rtl] .sc-ion-popover-ios-h .popover-arrow.sc-ion-popover-ios:after, [dir=rtl].sc-ion-popover-ios .popover-arrow.sc-ion-popover-ios:after{left:unset;right:unset;right:3px}.popover-bottom.sc-ion-popover-ios-h .popover-arrow.sc-ion-popover-ios{top:auto;bottom:-10px}.popover-bottom.sc-ion-popover-ios-h .popover-arrow.sc-ion-popover-ios:after{top:-6px}.popover-translucent.sc-ion-popover-ios-h .popover-arrow.sc-ion-popover-ios:after, .popover-translucent.sc-ion-popover-ios-h .popover-content.sc-ion-popover-ios{background:rgba(var(--ion-background-color-rgb,255,255,255),.8);-webkit-backdrop-filter:saturate(180%) blur(20px);backdrop-filter:saturate(180%) blur(20px)}"; }
}
const LIFECYCLE_MAP = {
    'ionPopoverDidPresent': 'ionViewDidEnter',
    'ionPopoverWillPresent': 'ionViewWillEnter',
    'ionPopoverWillDismiss': 'ionViewWillLeave',
    'ionPopoverDidDismiss': 'ionViewDidLeave',
};

exports.ion_popover = Popover;
