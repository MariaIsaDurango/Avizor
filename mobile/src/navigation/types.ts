import { Alert } from '../services/alerts';

export type RootStackParamList = {
  Welcome: undefined;
  ModeSelection: undefined;
  SeniorConsent: undefined;
  TutorLogin: undefined;
  TutorRegister: undefined;
  TutorPairing: undefined;
  TutorDashboard: undefined;
  TutorLogout: undefined;
  AlertDetail: { alert: Alert };
  SeniorHome: undefined;
};
