<template>
  <div>
    <div class="actions mb-3">
      <h1 class="d-inline" color="primary" text>Virtual Machines</h1>
      <v-btn
        class="float-right p-4"
        color="primary"
        text
        @click.stop="openChatflow('vmachine')"
      >
        <v-icon left>mdi-plus</v-icon>Add Virtual Machine
      </v-btn>
    </div>

    <v-data-table
      :headers="headers"
      :items="getVms()"
      :loading="loading || tableloading"
      class="elevation-1"
    >
      <template slot="no-data">No virtual machines available</template>
      <template v-slot:item.wid="{ item }">
        <div>{{ item.wid }}</div>
      </template>

      <template v-slot:item.public_ip="{ item }">
        <div>{{ item.public_ip.address }}</div>
      </template>

      <template v-slot:item.name="{ item }">
        <div>{{ item.name }}</div>
      </template>

      <template v-slot:item.cpu="{ item }">
        <div>{{ item.resources.cru }}</div>
      </template>

      <template v-slot:item.memory="{ item }">
        <div>{{ item.resources.mru }}</div>
      </template>
      <template v-slot:item.disk="{ item }">
        <div>{{ item.resources.sru }} GB</div>
      </template>

      <template v-slot:item.actions="{ item }">
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn icon @click.stop="open(item)">
              <v-icon v-bind="attrs" v-on="on" color="#206a5d"
                >mdi-information-outline</v-icon
              >
            </v-btn>
          </template>
          <span>Show Information</span>
        </v-tooltip>

        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn icon @click.stop="deleteVm(item.wid)">
              <v-icon v-bind="attrs" v-on="on" color="#810000"
                >mdi-delete</v-icon
              >
            </v-btn>
          </template>
          <span>Delete</span>
        </v-tooltip>
      </template>
    </v-data-table>

    <solution-info
      v-if="selected"
      v-model="dialogs.info"
      :data="selected"
      :keyswithtypedictprop="['public_ip','resources']"
    ></solution-info>

    <cancel-workload
      v-if="selectedvm"
      v-model="dialogs.cancelWorkload"
      api="deleteVm"
      title="Delete VM"
      :messages="deletionMessages"
      :wid="selectedvm"
      @reload-vdcinfo="removeVm()"
    ></cancel-workload>
  </div>
</template>

<script>
module.exports = {
  props: {
    vmachines: {
      type: Array,
      default: () => [],
    },
    tableloading: {
      type: Boolean,
      default: false,
    },
  },
  mixins: [dialog],
  components: {
    "solution-info": httpVueLoader("../base/Info.vue"),
    "cancel-workload": httpVueLoader("./DeleteConfirmation.vue"),
  },
  data() {
    return {
      selected: null,
      selectedvm: null,
      headers: [
        { text: "WID", value: "wid" },
        { text: "IP Address", value: "public_ip" },
        { text: "Name", value: "name" },
        { text: "CPUs", value: "cpu" },
        { text: "Memory", value: "memory" },
        { text: "Disk Size", value: "disk" },
        { text: "Actions", value: "actions", sortable: false },
      ],
      dialogs: {
        info: false,
        cancelWorkload: false,
      },
      deletionMessages: {
        confirmationMsg:
          "Are you sure you want to delete this virtual machine?",
        successMsg: "Virtual machine deleted successfully",
      },
      deletedVms: []
    };
  },
  methods: {
    open(record) {
      this.selected = record;
      this.dialogs.info = true;
    },
    deleteVm(wid) {
      this.selectedvm = wid;
      this.dialogs.cancelWorkload = true;
    },
    openChatflow(topic) {
      this.$router.push({
        name: "SolutionChatflow",
        params: { topic: topic },
      });
    },
    removeVm() {
      this.deletedVms.push(this.selectedvm);
    },
    getVms() {
      return this.vmachines.filter(({wid}) => !(this.deletedVms.includes(wid)))
    }
  }
};
</script>

<style scoped>
h1 {
  color: #1b4f72;
}
</style>
