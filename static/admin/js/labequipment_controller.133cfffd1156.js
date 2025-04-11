// myapp/static/js/example.js

class LabEquipmentTagController extends window.StimulusModule.Controller {
    static targets = ['label'];
    connect() {
        console.log(
            'My controller has connected:',
            this.element.innerText,
            this.labelTargets,
        );
    }
}

window.wagtail.app.register('lab-equipment-controller', LabEquipmentTagController);
