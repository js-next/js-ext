<template>
  <v-app>
    <v-app-bar v-if="topheader" app>
      <img src="/chatflows/static/assets/images/3bot.png" width="24"/>
      <v-spacer></v-spacer>
      <v-menu v-model="menu" :close-on-content-click="false" :nudge-width="200" offset-x>
        <template v-slot:activator="{ on }">
          <v-btn text v-on="on">
            <v-icon left>mdi-account</v-icon> {{userInfo.username}}
          </v-btn>
        </template>
        <v-card>
          <v-list>
            <v-list-item>
              <v-list-item-avatar>
                <v-avatar color="primary">
                  <v-icon dark>mdi-account-circle</v-icon>
                </v-avatar>
              </v-list-item-avatar>
              <v-list-item-content>
                <v-list-item-title>{{userInfo.username}}</v-list-item-title>
                <v-list-item-subtitle>{{userInfo.email}}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
          <v-divider></v-divider>
          <v-card-actions>
            <v-btn block text>
              <v-icon color="gray" class="mr-2" left>mdi-logout-variant</v-icon> Logout
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>

    </v-app-bar>
    <v-main>
      <div class="chat-container text-center">
          <h1 class="display-2 font-weight-light">{{title}}</h1><br><br>

          <v-card v-if="work" :disabled="loading" :loading="loading" class="mx-auto" width="70%" min-height="350" raised shaped>
            <div class="chat">
              <v-toolbar flat>
                <v-toolbar-title v-if="work.info.title" class="headline font-regular primary--text">
                  {{work.info.title}}
                </v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn color="primary" @click="restart" icon large>
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-toolbar>

              <v-card-text style="text-align:left">
                <v-form ref="form" :lazy-validation="true" @submit.prevent>
                  <component
                    v-model="state[stepId]"
                    :key="stepId"
                    :is="categories[this.work.payload.category]"
                    :payload="this.work.payload"
                  />
                </v-form>

              </v-card-text>

              <div class="text-center mt-10">
                <v-icon style="opacity: 0.8; padding-left:1px" x-small v-for="i in work.info.steps" :key="i" :color="i <= work.info.step ? 'primary' : '#E5E7E9'">mdi-checkbox-blank-circle</v-icon>
              </div>

              <v-card-actions>
                <v-btn color="primary" raised x-large class="px-5" min-width="120" @click="back" :disabled="backButtonDisable">
                  {{work.info.first_slide ? 'Previous step' : 'Back'}}
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" raised x-large class="px-5" min-width="120" @click="next" :loading="loading" :disabled="nextButtonDisable">{{nextButtonText}}</v-btn>
              </v-card-actions>
            </div>
          </v-card>
      </div>
    </v-main>
  </v-app>
</template>

<script>

  const axios = require('axios')
  const baseUrl = "/chatflows/actors/chatbot"

  module.exports =  {
    data () {
      return {
        state: {},
        sessionId: null,
        validSession: null,
        work: null,
        loading: true,
        menu: false,
        chat: CHAT,
        title: null,
        package: PACKAGE,
        userInfo: {username: USERNAME, email: EMAIL}
      }
    },
    computed: {
      topheader () {
        return window.self === window.top
      },
      chatUID () {
        return `${this.package}_${this.chat}`
      },
      nextButtonDisable () {
        return ['error', 'loading', 'infinite_loading'].includes(this.work.payload.category)
      },
      backButtonDisable () {
        return !this.work.info.previous || ['error', 'loading', 'infinite_loading'].includes(this.work.payload.category)
      },
      nextButtonText () {
        return this.work.info.final_step ? "Finish" : "Next"
      },
      stepId () {
        return `${this.work.info.step}_${this.work.info.slide}`
      }
    },
    methods: {
      validate() {
        return this.$refs["form"].validate()
      },
      handleResponse (response) {
        let payload = response.payload
        let end = false
        switch (payload.category) {
          case 'end':
            end = true
            localStorage.removeItem(this.chatUID)
            window.parent.postMessage("chat ended: " + this.chat, location.origin)
            break
          case 'user_info':
            this.sendUserInfo()
            break
          case 'redirect':
            this.redirect(payload.url)
          default:
            this.handlerWork(response)
        }
        if (end === false) this.getWork()
      },
      handlerWork (work) {
        this.work = work
        if (this.state[this.stepId] === undefined) {
          if (['form', 'multi_choice', 'multi_list_choice', 'location_ask'].includes(this.work.payload.category)) {
            this.$set(this.state, this.stepId, Array())
          }
        }
      },
      redirect (url) {
        location.href = url
      },
      sendUserInfo () {
        this.reportWork(JSON.stringify(this.userInfo))
      },
      saveSession (data) {
        let session = {
          id: this.sessionId,
          state: this.state,
          title: this.title,
          final: data.info ? data.info.final_step : false
        }
        localStorage.setItem(this.chatUID, JSON.stringify(session))
      },
      getSession () {
        let session = localStorage.getItem(this.chatUID)
        if (session) {
          return JSON.parse(session)
        }
      },
      start () {
        let session = this.getSession()
        if (session && !session.final) {
          this.validateSession(session.id).then(() => {
            if(this.validSession) {
              this.restoreSession(session)
            } else {
              localStorage.removeItem(this.chatUID)
              this.newSession()
            }
          })
        } else {
          this.newSession()
        }
      },
      validateSession(sessionId) {
        return axios({
          url: `${baseUrl}/validate?timestamp=${new Date().getTime()}`,
          method: "post",
          headers: {'Content-Type': 'application/json'},
          data: {
            session_id: sessionId,
          }
        }).then((response) => {

          this.validSession = response.data.valid
        })
      },
      newSession () {
        axios({
          url: `${baseUrl}/new`,
          method: "post",
          headers: {'Content-Type': 'application/json'},
          data: {
            package: this.package,
            chat: this.chat,
            client_ip: CLIENT_IP,
            query_params: this.$route.query
          }
        }).then((response) => {
            this.sessionId = response.data.sessionId
            this.title = response.data.title
            console.log(this.sessionId)
            this.getWork()
        })
      },
      restoreSession (session) {
        this.sessionId = session.id
        this.state = session.state
        this.title = session.title
        this.getWork(true)
      },
      getWork (restore) {
        failureMax = 60
        failureCount = 0

        const innerAxios = (failureCount) => {
              if (failureCount == failureMax) {
                  alert(`Connectivity error, we tried for ${failureCount} seconds, but Request timedout. please refresh the page.`)
                  return
              }
              return axios({
                  url: `${baseUrl}/fetch`,
                  method: "post",
                  data: {
                    session_id: this.sessionId,
                    restore: restore
                  }
                }).then((response) => {
                    this.loading = false
                    this.saveSession(response.data)
                    this.handleResponse(response.data)
                    return
                }).catch((response) => {
                      setTimeout(() => {
                        console.log(`retrying ... ${failureCount}`);
                        failureCount++;
                        return innerAxios(failureCount)
                      }, 1000);

                })

        }
        return innerAxios(failureCount)

      },
      reportWork (result) {
        axios({
          url: `${baseUrl}/report`,
          method: "post",
          data: {
            session_id: this.sessionId,
            result: result
          }
        })
      },
      next () {
        if (this.validate()) {
          let result = this.state[this.stepId]

          if (typeof result === 'object' || typeof result === 'number') {
            result = JSON.stringify(result)
          }

          this.loading = true
          this.reportWork(result)
        }
      },
      back () {
        axios({
          url: `${baseUrl}/back`,
          method: "post",
          data: {
            session_id: this.sessionId,
          }
        })
      },
      restart () {
        axios({
          url: `${baseUrl}/end`,
          method: "post",
          data: {
            session_id: this.sessionId,
          }
        }).then(() => {
          localStorage.removeItem(this.chatUID);
          location.reload();
        })
      },
      getCookie(cname) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for(var i = 0; i < ca.length; i++) {
          var c = ca[i];
          while (c.charAt(0) == ' ') {
            c = c.substring(1);
          }
          if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
          }
        }
        return "";
      },
      checkDarkMode(){
        let cookie = this.getCookie("darkTheme")
        if (cookie == "")
          this.$vuetify.theme.dark = false
        else
          this.$vuetify.theme.dark = cookie == "1" ? true : false;
      }
    },
    mounted () {
      this.checkDarkMode()
      this.start()
      document.body.addEventListener('keypress', (e) => {
        if (e.key == 'Enter') {
          this.next()
        }
      })
    }
  }
</script>
