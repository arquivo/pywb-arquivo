import { r as registerInstance, d as getIonMode, h, H as Host } from './chunk-f257aad1.js';
import './chunk-1074393c.js';
import { c as createColorClasses } from './chunk-9d21e8e5.js';
/**
 * @virtualProp {"ios" | "md"} mode - The mode determines which platform styles to use.
 */
var Text = /** @class */ (function () {
    function Text(hostRef) {
        registerInstance(this, hostRef);
    }
    Text.prototype.hostData = function () {
        var _a;
        var mode = getIonMode(this);
        return {
            class: Object.assign({}, createColorClasses(this.color), (_a = {}, _a[mode] = true, _a))
        };
    };
    Text.prototype.__stencil_render = function () {
        return h("slot", null);
    };
    Text.prototype.render = function () { return h(Host, this.hostData(), this.__stencil_render()); };
    Object.defineProperty(Text, "style", {
        get: function () { return ":host(.ion-color){color:var(--ion-color-base)}"; },
        enumerable: true,
        configurable: true
    });
    return Text;
}());
export { Text as ion_text };
