import { Alert } from '../services/alerts';
import { BlockTemplate } from '../services/analyses';

export type RootStackParamList = {
  Welcome: undefined;
  ModeSelection: undefined;
  SeniorConsent: undefined;
  TutorLogin: { email?: string } | undefined;
  TutorRegister: undefined;
  TutorPairing: undefined;
  TutorDashboard: undefined;
  TutorLogout: undefined;
  AlertDetail: { alert: Alert };
  SeniorPairing: undefined;
  SeniorHome: undefined;
  SeniorSettings: undefined;
  SeniorBlock: { template: BlockTemplate };
  AccessibilityPoc: undefined;
  VerifyEmail: { email: string };
  CallScreeningPoc: undefined;
  NotificationPoc: undefined;
};
