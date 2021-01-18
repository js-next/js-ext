<template>
  <v-snackbar v-model="show" :color="status" :timeout="5000">
    {{ msg }}
  </v-snackbar>
</template>

<script>
module.exports = {
  data () {
    return {
      show: false,
      msg: null,
      status: 'success'
    }
  },
  mounted () {
    this.$root.$on('popup', (msg, status) => {
      this.show = true
      this.msg = msg
      this.status = status
    })
  }
}
</script>
