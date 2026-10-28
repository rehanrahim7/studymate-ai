import {
  CircleHelp,
  FileText,
  History,
  LayoutDashboard,
  Layers,
  MessagesSquare,
  ScrollText,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Short status shown next to the label, e.g. `Soon`. */
  badge?: string
  description: string
}

export interface NavSection {
  title: string
  items: NavItem[]
}

/** Navigation shared by the desktop sidebar and the mobile drawer. */
export const navSections: NavSection[] = [
  {
    title: 'Workspace',
    items: [
      {
        label: 'Dashboard',
        to: '/',
        icon: LayoutDashboard,
        description: 'Overview of your library and study tools.',
      },
      {
        label: 'Documents',
        to: '/documents',
        icon: FileText,
        description: 'Manage the PDFs you have uploaded.',
      },
    ],
  },
  {
    title: 'Study tools',
    items: [
      {
        label: 'Chat',
        to: '/chat',
        icon: MessagesSquare,
        description: 'Ask questions and get answers with page citations.',
      },
      {
        label: 'Summaries',
        to: '/summaries',
        icon: ScrollText,
        description: 'Generate concise, structured summaries of a document.',
      },
      {
        label: 'Flashcards',
        to: '/flashcards',
        icon: Layers,
        description: 'Turn key concepts into revision flashcards.',
      },
      {
        label: 'Quizzes',
        to: '/quizzes',
        icon: CircleHelp,
        description: 'Practice with multiple-choice quizzes from your notes.',
      },
      {
        label: 'Study History',
        to: '/history',
        icon: History,
        description: 'Reopen saved flashcard decks and quizzes.',
      },
    ],
  },
  {
    title: 'Preferences',
    items: [
      {
        label: 'Settings',
        to: '/settings',
        icon: Settings,
        description: 'Theme and backend status.',
      },
    ],
  },
]

/** Flat list of every route, used to resolve page titles. */
export const allNavItems: NavItem[] = navSections.flatMap((section) => section.items)
