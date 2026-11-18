import { StyleSheet } from 'react-native';
import { colors } from '../constants/colors';

export const authStyles = StyleSheet.create({
  back: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 16,
    marginBottom: 20,
  },
  backText: {
    fontSize: 14,
    color: colors.primary,
    opacity: 0.65,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 24,
  },
  logo: {
    width: 32,
    height: 32,
  },
  brandName: {
    fontSize: 22,
    fontStyle: 'italic',
    color: colors.primary,
  },
  heading: {
    fontSize: 22,
    fontWeight: '300',
    color: colors.primary,
    textAlign: 'center',
    marginBottom: 4,
    lineHeight: 28,
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  subtitleBold: {
    fontWeight: '600',
    color: colors.primary,
  },
  alertError: {
    backgroundColor: '#fde8e8',
    borderWidth: 1,
    borderColor: '#fca5a5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  alertErrorText: {
    fontSize: 13,
    color: '#b91c1c',
  },
  alertSuccess: {
    backgroundColor: '#d1f0de',
    borderWidth: 1,
    borderColor: '#a8d9b8',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  alertSuccessText: {
    fontSize: 13,
    color: colors.success,
  },
  formGroup: {
    gap: 4,
    marginBottom: 14,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.primary,
  },
  hint: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 2,
  },
  input: {
    borderWidth: 1.5,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: colors.primary,
    backgroundColor: colors.white,
  },
  inputWrap: {
    position: 'relative',
  },
  inputWithEye: {
    paddingRight: 44,
  },
  eyeBtn: {
    position: 'absolute',
    right: 12,
    top: 10,
  },
  submitBtn: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  submitBtnDisabled: {
    opacity: 0.65,
  },
  submitText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: '600',
  },
  footerLink: {
    alignItems: 'center',
    marginTop: 14,
  },
  footerText: {
    fontSize: 13,
    color: '#6b7280',
  },
  footerTextBold: {
    color: colors.primary,
    fontWeight: '600',
  },
});
