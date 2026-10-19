import type {
  University,
  Scholarship,
  StudyPlan,
  FinancialPlan,
  Student,
  PreparationTask,
} from "@/types";
export const universities: University[] = [
  {
    id: "tsinghua",
    name: "Tsinghua University",
    shortName: "TH",
    country: "China",
    city: "Beijing",
    tuition: 30000,
    living: 4200,
    scholarship: true,
    color: "violet",
    description:
      "Explore a research-focused campus in Beijing with a broad selection of academic disciplines.",
    programs: [
      {
        id: "th-cs",
        subject: "Computer Science",
        degree: "Master",
        language: "English / Chinese",
        duration: 3,
      },
      {
        id: "th-eng",
        subject: "Engineering",
        degree: "Bachelor",
        language: "Chinese",
        duration: 4,
      },
    ],
  },
  {
    id: "zhejiang",
    name: "Zhejiang University",
    shortName: "ZU",
    country: "China",
    city: "Hangzhou",
    tuition: 28000,
    living: 3500,
    scholarship: true,
    color: "blue",
    description:
      "Discover an interdisciplinary study environment in the lakeside city of Hangzhou.",
    programs: [
      {
        id: "zu-cs",
        subject: "Computer Science",
        degree: "Master",
        language: "English / Chinese",
        duration: 3,
      },
      {
        id: "zu-bus",
        subject: "Business",
        degree: "Bachelor",
        language: "Chinese",
        duration: 4,
      },
    ],
  },
  {
    id: "fudan",
    name: "Fudan University",
    shortName: "FU",
    country: "China",
    city: "Shanghai",
    tuition: 35000,
    living: 5000,
    scholarship: true,
    color: "teal",
    description:
      "Consider a city-based academic experience with humanities, business, and research pathways.",
    programs: [
      {
        id: "fu-bus",
        subject: "Business",
        degree: "Master",
        language: "English",
        duration: 2,
      },
      {
        id: "fu-med",
        subject: "Medicine",
        degree: "PhD",
        language: "Chinese",
        duration: 4,
      },
    ],
  },
  {
    id: "wuhan",
    name: "Wuhan University",
    shortName: "WU",
    country: "China",
    city: "Wuhan",
    tuition: 24000,
    living: 2800,
    scholarship: true,
    color: "amber",
    description:
      "Explore a multidisciplinary campus and a range of illustrative postgraduate pathways.",
    programs: [
      {
        id: "wu-eng",
        subject: "Engineering",
        degree: "Master",
        language: "English / Chinese",
        duration: 3,
      },
      {
        id: "wu-med",
        subject: "Medicine",
        degree: "Bachelor",
        language: "English",
        duration: 6,
      },
    ],
  },
  {
    id: "nanjing",
    name: "Nanjing University",
    shortName: "NU",
    country: "China",
    city: "Nanjing",
    tuition: 26000,
    living: 3200,
    scholarship: false,
    color: "rose",
    description:
      "Build a shortlist around science, research, and a historic university city.",
    programs: [
      {
        id: "nu-cs",
        subject: "Computer Science",
        degree: "PhD",
        language: "English / Chinese",
        duration: 4,
      },
      {
        id: "nu-eng",
        subject: "Engineering",
        degree: "Bachelor",
        language: "Chinese",
        duration: 4,
      },
    ],
  },
  {
    id: "sjtu",
    name: "Shanghai Jiao Tong University",
    shortName: "SJ",
    country: "China",
    city: "Shanghai",
    tuition: 32000,
    living: 4800,
    scholarship: true,
    color: "blue",
    description:
      "Investigate engineering and technology study options in a major global city.",
    programs: [
      {
        id: "sj-eng",
        subject: "Engineering",
        degree: "Master",
        language: "English",
        duration: 3,
      },
      {
        id: "sj-bus",
        subject: "Business",
        degree: "PhD",
        language: "English / Chinese",
        duration: 4,
      },
    ],
  },
];
export const scholarships: Scholarship[] = [
  {
    id: "government",
    name: "Government scholarship pathway",
    country: "China",
    degrees: ["Master", "PhD"],
    funding: "Full",
    description:
      "A sample entry illustrating a government-funded research pathway. No current award or eligibility is verified.",
    coverage:
      "Illustrative tuition, accommodation, and stipend coverage; confirm each component with the awarding body.",
  },
  {
    id: "university",
    name: "University merit scholarship",
    country: "China",
    degrees: ["Bachelor", "Master"],
    funding: "Partial",
    description:
      "An illustrative university-level award for your planning shortlist.",
    coverage:
      "Sample tuition contribution. Amount, renewal terms, and availability require verification.",
  },
  {
    id: "research",
    name: "Graduate research award",
    country: "China",
    degrees: ["PhD"],
    funding: "Full",
    description:
      "A sample research-funding opportunity to discuss with prospective departments.",
    coverage:
      "Illustrative tuition support and research allowance. No funding is guaranteed.",
  },
  {
    id: "city",
    name: "City study grant",
    country: "China",
    degrees: ["Bachelor", "Master", "PhD"],
    funding: "Partial",
    description:
      "An example of a local study grant category, included for discovery practice.",
    coverage:
      "Sample annual grant; check official local authority and university information.",
  },
];
export const student: Student = {
  fullName: "Alex Morgan",
  nationality: "Bangladesh",
  currentCountry: "Bangladesh",
  destination: "China",
  education: "Bachelor",
  background: "Computer science undergraduate",
  subject: "Computer Science",
  budget: 100000,
  language: "English — intermediate",
  scholarship: true,
  careerGoals: "Build a career in technology and research.",
};
export const studyPlan: StudyPlan = {
  destination: "China",
  goal: "Master’s in Computer Science",
  intake: "September 2027",
  tasks: [
    {
      id: "profile",
      title: "Complete your student profile",
      description: "Add your academic background and study preferences.",
    },
    {
      id: "shortlist",
      title: "Build a university shortlist",
      description: "Compare programs, cities, and illustrative costs.",
    },
    {
      id: "funding",
      title: "Explore funding options",
      description: "Save scholarship categories to investigate.",
    },
    {
      id: "documents",
      title: "Prepare an academic document checklist",
      description:
        "Identify official requirements directly with your chosen university.",
    },
  ],
};
export const defaultPlan: FinancialPlan = {
  country: "China",
  university: "zhejiang",
  years: 3,
  tuition: 28000,
  accommodation: 1800,
  food: 1000,
  transportation: 200,
  insurance: 800,
  other: 500,
  scholarship: 12000,
  relocation: 6000,
  emergency: 10000,
  currency: "CNY",
};
export const lifeTasks: PreparationTask[] = [
  {
    id: "passport",
    title: "Review important documents",
    description:
      "Check passport validity and obtain the current document list from your institution.",
  },
  {
    id: "arrival",
    title: "Plan your arrival",
    description:
      "Confirm airport transfer, arrival contact, and temporary accommodation.",
  },
  {
    id: "housing",
    title: "Research accommodation",
    description:
      "Compare university housing with independently verified rental options.",
  },
  {
    id: "transport",
    title: "Map your daily commute",
    description: "Research campus transport and local travel options.",
  },
  {
    id: "banking",
    title: "Prepare banking and mobile services",
    description:
      "Ask local providers about identification requirements and fees.",
  },
  {
    id: "health",
    title: "Review health insurance",
    description:
      "Confirm coverage, exclusions, and institution requirements with the insurer.",
  },
];
export const careerTasks: PreparationTask[] = [
  {
    id: "explore",
    title: "Explore career directions",
    description:
      "Map roles in software engineering, research, and product development to your interests.",
  },
  {
    id: "skills",
    title: "Create a skills portfolio",
    description: "Choose one practical project and document your learning.",
  },
  {
    id: "cv",
    title: "Prepare your CV",
    description:
      "Describe your projects, academic experience, and transferable skills.",
  },
  {
    id: "internship",
    title: "Research internship resources",
    description:
      "Explore your university career office and verify employer and authorization requirements.",
  },
  {
    id: "pathways",
    title: "Investigate post-graduation pathways",
    description:
      "Consult official authorities and qualified advisers for current immigration and work rules.",
  },
];
