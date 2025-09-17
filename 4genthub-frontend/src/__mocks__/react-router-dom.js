module.exports = {
  useNavigate: jest.fn(() => jest.fn()),
  useLocation: jest.fn(() => ({ pathname: '/' })),
  useParams: jest.fn(() => ({})),
  Link: ({ children, to, ...props }) => children,
  NavLink: ({ children, to, ...props }) => children,
};