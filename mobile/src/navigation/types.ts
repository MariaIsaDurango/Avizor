import { Alert } from '../services/alerts';
import { BlockTemplate } from '../services/analyses';

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
  SeniorPairing: undefined;
  SeniorHome: undefined;
  SeniorBlock: { template: BlockTemplate };
};
