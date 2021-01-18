<template>
  <v-card :width="width || '100%'" height="auto" :loading="loading">
    <v-toolbar dense flat>
      <v-toolbar-title class="primary--text">
        <v-icon color="primary" left>{{icon}}</v-icon> {{title}}
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <slot name="actions"></slot>
    </v-toolbar>
    <v-divider></v-divider>
    <v-card-text>
      <slot name="default"></slot>
    </v-card-text>
  </v-card>
</template>

<script>
  module.exports = {
    props: {
      title: String,
      icon: String,
      loading: Boolean,
      width: String
    }
  }
</script>
