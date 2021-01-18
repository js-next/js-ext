<template>
  <v-dialog v-model="dialog" width="1000" :retain-focus="false" :persistent="persistent">
    <v-card :loading="loading" :disabled="loading">
      <v-card-title class="headline">{{title}}</v-card-title>
      <v-card-text class="pa-5">
        <v-alert v-if="error" dense outlined type="error" class="mb-5">{{error}}</v-alert>

        <v-alert v-if="info" dense outlined type="info" class="mb-5">{{info}}</v-alert>

        <v-alert v-if="warning" dense outlined type="warning" class="mb-5">{{warning}}</v-alert>

        <slot name="default"></slot>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <slot name="actions"></slot>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
module.exports = {
  props: {
    value: Boolean,
    title: String,
    error: String,
    info: String,
    warning: String,
    loading: Boolean,
    persistent: {
      type: Boolean,
      default: false
    },
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      },
    },
  },
};
</script>
