const DOCS_BASE_URL = "https://marketplace.threefold.io/apps"

const DECENTRALIZED_OFFICE = {
    titleToolTip: null,
    apps: {
        taiga: {
            name: "Taiga",
            type: "taiga",
            image: "./assets/taiga.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/taiga`,
            description: "Taiga is a P2P alternative to centralized project management tool for multi-functional agile teams."
        },
        cryptpad: {
            name: "Cryptpad",
            type: "cryptpad",
            image: "./assets/cryptpad.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/cryptpad`,
            description: "Cryptpad is a fully-secured, encrypted alternative to popular office tools and cloud services."
        },
        mattermost: {
            name: "Mattermost",
            type: "mattermost",
            image: "./assets/mattermost.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/mattermost`,
            description: "Mattermost is a flexible, open source messaging platform that enables secure team collaboration."
        },
        documentserver: {
            name: "Document Server",
            type: "documentserver",
            image: "./assets/document_server.jpg",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/document_server`,
            description: "Document Server is a free collaborative online office suite comprising viewers and editors for texts, spreadsheets and presentations, fully compatible with Office Open XML formats: .docx, .xlsx, .pptx and enabling collaborative editing in real time"
        },
        filebrowser: {
            name: "File Browser",
            type: "filebrowser",
            image: "./assets/file_browser.jpg",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/file_browser`,
            description: "File browser is an open source solution that provides a file managing interface"
        },
        crm: {
            name: "CRM",
            type: "crm",
            image: "./assets/crm.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/crm`,
            description: "Full featured Customer Relationship Management system."
        },
    },
}


const DECENTRALIZED_WE = {
    titleToolTip: null,
    apps: {
        blog: {
            name: "Blog",
            type: "blog",
            image: "./assets/blog.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/blog_publisher`,
            description: "Blog is a P2P alternative to centralized blogging platforms like Tumblr or Blogspot."
        },
        website: {
            name: "Website",
            type: "website",
            image: "./assets/web.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/website_publisher`,
            description: "Website is a P2P alternative to centralized cloud-hosted websites. Host your own website with access via a public web address."
        },

        wiki: {
            name: "Wiki",
            type: "wiki",
            image: "./assets/doc-flat.svg",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/wiki_publisher`,
            description: "Wiki is a versatile online encyclopedia builder, accessible via a public web address."
        },
        discourse: {
            name: "Discourse",
            type: "discourse",
            image: "./assets/discourse.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/discourse`,
            description: "Discourse is an open source Internet forum and mailing list management software application built to educate members about civil community engagement."
        },
        mastodon: {
            name: "Mastodon",
            type: "mastodon",
            image: "./assets/mastodon.png",
            disable: false,
            helpLink: "https://docs.joinmastodon.org/",
            description: "Similar to how blogging is the act of publishing updates to a website, microblogging is the act of publishing small updates to a stream of updates on your profile. You can publish text posts and optionally attach media such as pictures, audio, video, or polls. Mastodon lets you follow friends and discover new ones."
        },
        peertube: {
            name: "Peertube",
            type: "peertube",
            image: "./assets/peertube.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/peertube`,
            description: "Peertube is an open-source video platform that uses peer-to-peer technologies to reduce load on individual servers when viewing videos."
        },
        owncloud: {
            name: "Owncloud",
            type: "owncloud",
            image: "./assets/owncloud.png",
            disable: false,
            helpLink: "https://doc.owncloud.com/server/10.6/",
            description: "ownCloud is a suite of client-server software for creating and using file hosting services. ownCloud functionally has similarities to the widely used Dropbox."
        },
        owncloud1080: {
            name: "Owncloud 10.8.0",
            type: "owncloud1080",
            image: "./assets/owncloud.png",
            disable: false,
            helpLink: "https://doc.owncloud.com/server/10.8/",
            description: "ownCloud is a suite of client-server software for creating and using file hosting services. ownCloud functionally has similarities to the widely used Dropbox."
        },
        meetings: {
            name: "Video Chat",
            type: "meetings",
            image: "./assets/video_chat.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/video_chat`,
            description: "P2P alternative to centralised video conferencing solution such as Zoom."
        },
        virtualspaces: {
            name: "Virtual Spaces",
            type: "virtualspaces",
            image: "./assets/virtual_spaces.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/virtual_spaces`,
            description: "Meetup experiences and collaboration in virtual reality."
        },
        knowledgebase: {
            name: "Knowledge Base",
            type: "knowledgebase",
            image: "./assets/_base.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/knowledge_base`,
            description: "A simple, self-hosted, easy-to-use platform for organizing and storing information."
        },
        commento: {
            name: "Commento",
            type: "commento",
            image: "./assets/commento.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/commento`,
            description: "Commento lets you embed comments without giving up your privacy."
        },
    },
}

const DECENTRALIZED_DEV = {
    titleToolTip: null,
    apps: {
        gitea: {
            name: "Gitea",
            type: "gitea",
            image: "./assets/gitea.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/gitea`,
            description: "Gitea is a painless self-hosted Git service. It is similar to GitHub, Bitbucket, and GitLab."
        },
        serverless: {
            name: "Serverless",
            type: "serverless",
            image: "./assets/serverless.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/serverless`,
            description: "Collaborate on online content without giving up your privacy."
        },
        gridsome: {
            name: "Gridsome",
            type: "gridsome",
            image: "./assets/gridsome.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/gridsome`,
            description: "Gridsome makes it easy to build Jamstack websites using data from multiple sources."
        },
        monitoringstack: {
            name: "Monitoring Stack",
            type: "monitoringstack",
            image: "./assets/monitoring.png",
            disable: false,
            helpLink: "",
            description: "Monitoring Stack makes it easy to monitor your VDC using Grafana, Prometheus, Redis"
        },
        zeroci: {
            name: "ZeroCI",
            type: "zeroci",
            image: "./assets/zero-ci-dark.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/zeroci`,
            description: "Continuous integration system useful for all programming languages."
        },
        kubeapps: {
            name: "Kubeapps",
            type: "kubeapps",
            image: "./assets/kubeapps.png",
            disable: false,
            helpLink: "",
            description: "Kubeapps is a web-based UI for deploying and managing applications in Kubernetes clusters."
        },
        etcd: {
            name: "ETCD",
            type: "etcd",
            image: "./assets/etcd.png",
            disable: false,
            helpLink: "",
            description: "A distributed, reliable key-value store for the most critical data of a distributed system. Used by kubectl"
        },

        minio: {
            name: "Minio Quantum Storage",
            type: "minio",
            image: "./assets/minio.png",
            disable: false,
            helpLink: "",
            description: "Quantum Storage solution uses MinIO which is a high performance object storage. With the assist of the chatflow the user will deploy a machine with MinIO along with a number of zdbs needed for storage."
        },
    },
}

const BC_SOLUTIONS = {
    titleToolTip: null,
    apps: {
        dash: {
            name: "Dash",
            type: "dash",
            image: "./assets/dash.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/dash`,
            description: "Open source peer-to-peer cryptocurrency with a strong focus on the payments industry."
        },
        digibyte: {
            name: "DigiByte",
            type: "digibyte",
            image: "./assets/digibyte.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/digibyte`,
            description: "Safest, fastest, longest, and most decentralized UTXO blockchains in existence."
        },
        presearch: {
            name: "Presearch",
            type: "presearch",
            image: "./assets/presearch.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/presearch`,
            description: "Presearch is a decentralized search engine powered by blockchain technology."
        },
        elrond: {
            name: "Elrond",
            type: "elrond",
            image: "./assets/elrond.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/elrond`,
            description: "The internet-scale blockchain, designed from scratch to bring a 1000-fold cumulative improvement in throughput and execution speed."
        },
        harmony: {
            name: "Harmony",
            type: "harmony",
            image: "./assets/harmony.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/harmony`,
            description: "Fast and open blockchain for decentralized applications."
        },
        matic: {
            name: "Polygon",
            type: "matic",
            image: "./assets/polygon.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/polygon`,
            description: "Protocol and framework for building Ethereum-compatible blockchain networks."
        },
        neo: {
            name: "Neo",
            type: "neo",
            image: "./assets/neo.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/neo`,
            description: "Scalable, fast, and ultra-secure Blockchain drove by a global community of developers and node operators."
        },
        scale: {
            name: "Skale",
            type: "scale",
            image: "./assets/Skale.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/skalelabs`,
            description: "An elastic blockchain network that gives developers the ability to easily provision highly configurable chains compatible with Ethereum."
        },
        tomochain: {
            name: "TomoChain",
            type: "tomochain",
            image: "./assets/TomoChain.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/tomochain`,
            description: "Scalable blockchain-powered via Proof-of-Stake Voting consensus and used commercially by companies globally."
        },
        waykichain: {
            name: "WaykiChain",
            type: "waykichain",
            image: "./assets/WaykiChain.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/waykichain`,
            description: "Prominent blockchain platform based in China with a global community."
        },
        casperlabs: {
            name: "CasperLabs",
            type: "casperlabs",
            image: "./assets/casperlabs.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/casperlabs`,
            description: "CasperLabs is the team behind the Casper Network, first blockchain built for enterprise adoption"
        },
    },
}


const SECTIONS = {
    "All Solutions": {
        titleToolTip: null,
        apps: {
            ...DECENTRALIZED_OFFICE.apps,
            ...DECENTRALIZED_WE.apps,
            ...DECENTRALIZED_DEV.apps,
            ...BC_SOLUTIONS.apps,
        },
    },
    "Decentralized Office": DECENTRALIZED_OFFICE,
    "Decentralized WE": DECENTRALIZED_WE,
    "Decentralized Developer": DECENTRALIZED_DEV,
    "Blockchain Solutions": BC_SOLUTIONS,
}
const KUBERNETES_VM_SIZE_MAP =
{
    1: { "vcpu": 1, "memory": 2, "storage": 50 },
    2: { "vcpu": 2, "memory": 4, "storage": 100 },
    3: { "vcpu": 2, "memory": 8, "storage": 25 },
    4: { "vcpu": 2, "memory": 8, "storage": 50 },
    5: { "vcpu": 2, "memory": 8, "storage": 200 },
    6: { "vcpu": 4, "memory": 16, "storage": 50 },
    7: { "vcpu": 4, "memory": 16, "storage": 100 },
    8: { "vcpu": 4, "memory": 16, "storage": 400 },
    9: { "vcpu": 8, "memory": 32, "storage": 100 },
    10: { "vcpu": 8, "memory": 32, "storage": 200 },
    11: { "vcpu": 8, "memory": 32, "storage": 800 },
    12: { "vcpu": 16, "memory": 64, "storage": 200 },
    13: { "vcpu": 16, "memory": 64, "storage": 400 },
    14: { "vcpu": 16, "memory": 64, "storage": 800 },
    15: { "vcpu": 1, "memory": 2, "storage": 25 },
    16: { "vcpu": 2, "memory": 4, "storage": 50 },
    17: { "vcpu": 4, "memory": 8, "storage": 50 },
    18: { "vcpu": 1, "memory": 1, "storage": 25 },
}

const LEVELS = {
    50: { value: 50, text: "CRITICAL", color: "#A93226" },
    40: { value: 40, text: "ERROR", color: "#CB4335" },
    30: { value: 30, text: "WARNING", color: "#F39C12" },
    20: { value: 20, text: "INFO", color: "#148F77" },
    15: { value: 15, text: "STDOUT", color: "#5499C7" },
    10: { value: 10, text: "DEBUG", color: "#839192" }
};

const STATES = [
    'closed',
    'new',
    'open',
    'reopen'
]

const TYPES = [
    'bug',
    'question',
    'event_system',
    'event_monitor',
    'event_operator',
]

const USER_ROLES = [
    "ADMIN",
    "USER",
]
