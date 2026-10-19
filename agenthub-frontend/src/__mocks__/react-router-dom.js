module.exports = {
  useNavigate: jest.fn(() => jest.fn()),
  useLocation: jest.fn(() => ({ pathname: '/' })),
  useParams: jest.fn(() => ({})),
  Link: ({ children }) => children,
  NavLink: ({ children }) => children,
};
