/** @odoo-module */

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class UploadWidget extends Component {
   static template = "website_slides_attachment.large_file_upload_widget_template";
   static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
   };

   setup() {
      this.state = useState({
        file: null,
        filename: null,
        saveLocation: '',
        uploading: false,
      });
      this.name = null;
    }

    onFileChange(event) {
      this.state.filename = event.target.files[0].name;
      this.state.file = event.target.files[0];
    }
    onSaveLocationChange(event) {
      this.state.saveLocation = event.target.value;
      if (!this.state.saveLocation.startsWith('/')) {
        this.state.saveLocation = '/' + this.state.saveLocation;
      }
      if (!this.state.saveLocation.endsWith('/')) {
        this.state.saveLocation += '/';
      }
      document.querySelector('#save_location').value = this.state.saveLocation;
    }
   
      async startUpload() {
      if (!this.state.file) {
        alert('Please select a file to upload.');
        return;
      }
      if (!this.state.saveLocation) {
        alert('Please enter a save location.');
        return;
      }
      const date = new Date().toISOString();
      const formData = new FormData();
      formData.append('file', this.state.file);
      formData.append('time_stamp', date);
      formData.append('res_model', this.props.record._config.resModel);
      formData.append('save_location', this.state.saveLocation);

      this.state.uploading = true;
      await fetch('/website_slides_attachment/upload', {
        method: 'POST',
        body: formData,
      });
      this.props.record.dirty = true;
      this.props.record.data[this.props.name] = this.state.saveLocation + this.props.record._config.resModel + '_' + date + '_' + this.state.filename.replaceAll(' ', '_' );
      this.props.record._changes[this.props.name] = this.state.saveLocation + this.props.record._config.resModel + '_' + date + '_' + this.state.filename.replaceAll(' ', '_' );
      this.state.uploading = false;
    }
    async onRemove(){
      const formData = new FormData();
      formData.append('file_path', this.props.record.data[this.props.name]);

      await fetch('/website_slides_attachment/remove', {
        method: 'POST',
        body: formData,
      });

      this.props.record.dirty = true;
      this.props.record.data[this.props.name] = '';
      this.props.record._changes[this.props.name] = '';
    }
}

export const uploadWidget = {
    component: UploadWidget,
    displayName: _t("File"),
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        fileNameField: attrs.filename,
    }),
};
registry.category("fields").add("large_file_upload_widget", uploadWidget);
