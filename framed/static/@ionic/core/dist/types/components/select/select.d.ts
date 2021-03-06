import { ComponentInterface, EventEmitter } from '../../stencil.core';
import { SelectChangeEventDetail, SelectInterface, StyleEventDetail } from '../../interface';
import { SelectCompareFn } from './select-interface';
/**
 * @virtualProp {"ios" | "md"} mode - The mode determines which platform styles to use.
 */
export declare class Select implements ComponentInterface {
    private childOpts;
    private inputId;
    private overlay?;
    private didInit;
    private buttonEl?;
    el: HTMLIonSelectElement;
    isExpanded: boolean;
    /**
     * If `true`, the user cannot interact with the select.
     */
    disabled: boolean;
    /**
     * The text to display on the cancel button.
     */
    cancelText: string;
    /**
     * The text to display on the ok button.
     */
    okText: string;
    /**
     * The text to display when the select is empty.
     */
    placeholder?: string | null;
    /**
     * The name of the control, which is submitted with the form data.
     */
    name: string;
    /**
     * The text to display instead of the selected option's value.
     */
    selectedText?: string | null;
    /**
     * If `true`, the select can accept multiple values.
     */
    multiple: boolean;
    /**
     * The interface the select should use: `action-sheet`, `popover` or `alert`.
     */
    interface: SelectInterface;
    /**
     * Any additional options that the `alert`, `action-sheet` or `popover` interface
     * can take. See the [AlertController API docs](../../alert/AlertController/#create), the
     * [ActionSheetController API docs](../../action-sheet/ActionSheetController/#create) and the
     * [PopoverController API docs](../../popover/PopoverController/#create) for the
     * create options for each interface.
     */
    interfaceOptions: any;
    /**
     * A property name or function used to compare object values
     */
    compareWith?: string | SelectCompareFn | null;
    /**
     * the value of the select.
     */
    value?: any | null;
    /**
     * Emitted when the value has changed.
     */
    ionChange: EventEmitter<SelectChangeEventDetail>;
    /**
     * Emitted when the selection is cancelled.
     */
    ionCancel: EventEmitter<void>;
    /**
     * Emitted when the select has focus.
     */
    ionFocus: EventEmitter<void>;
    /**
     * Emitted when the select loses focus.
     */
    ionBlur: EventEmitter<void>;
    /**
     * Emitted when the styles change.
     * @internal
     */
    ionStyle: EventEmitter<StyleEventDetail>;
    disabledChanged(): void;
    valueChanged(): void;
    selectOptionChanged(): Promise<void>;
    componentDidLoad(): Promise<void>;
    /**
     * Open the select overlay. The overlay is either an alert, action sheet, or popover,
     * depending on the `interface` property on the `ion-select`.
     *
     * @param event The user interface event that called the open.
     */
    open(event?: UIEvent): Promise<any>;
    private createOverlay;
    private updateOverlayOptions;
    private createActionSheetButtons;
    private createAlertInputs;
    private createPopoverOptions;
    private openPopover;
    private openActionSheet;
    private openAlert;
    /**
     * Close the select interface.
     */
    private close;
    private loadOptions;
    private updateOptions;
    private getLabel;
    private hasValue;
    private getText;
    private setFocus;
    private emitStyle;
    private onClick;
    private onFocus;
    private onBlur;
    render(): any;
}
